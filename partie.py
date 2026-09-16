import json
import os
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

# ==========================================
# --- CONFIGURATION & FICHIERS ---
# ==========================================

CONFIG_FILE = "config.json"
TRIBUS_FILE = "tribus.json"
WARNS_FILE = "warns.json"

# IDs importants
ID_CATEGORIE_TRIBUS = 1548631055047860234  # ID de la catégorie où créer les salons
ID_ROLE_ADMIN = 1543664637546070217       # ID du rôle admin
ID_SALON_LOGS_WARNS = 1543670405523570808   # ID du salon de logs pour les sanctions

# Chargement du token du bot Discord principal
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)
    TOKEN = config.get("token")

# Gestion de la sauvegarde automatique dans tribus.json
def charger_tribus():
    if os.path.exists(TRIBUS_FILE):
        try:
            with open(TRIBUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def sauvegarder_tribus(tribus_data):
    with open(TRIBUS_FILE, "w", encoding="utf-8") as f:
        json.dump(tribus_data, f, indent=4, ensure_ascii=False)

# Gestion de la sauvegarde automatique dans warns.json
def charger_warns():
    if os.path.exists(WARNS_FILE):
        try:
            with open(WARNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def sauvegarder_warns(warns_data):
    with open(WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(warns_data, f, indent=4, ensure_ascii=False)

# ==========================================
# --- INITIALISATION BOT DISCORD ---
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes synchronisées : {len(synced)}")
    except Exception as e:
        print(e)


# ==========================================
# --- MODAL POUR MODIFIER LE PRIX ---
# ==========================================
class PriceModal(Modal, title="Modifier le prix de la demande"):
    nouveau_prix = TextInput(
        label="Nouveau prix unitaire",
        placeholder="Ex: 200",
        required=True,
    )

    def __init__(self, member: discord.Member, item: str, quantity: int, original_embed: discord.Embed):
        super().__init__()
        self.member = member
        self.item = item
        self.quantity = quantity
        self.original_embed = original_embed

    async def on_submit(self, interaction: discord.Interaction):
        prix = self.nouveau_prix.value

        try:
            await self.member.send(
                f"✅ Votre demande pour **{self.quantity} {self.item}** a été **acceptée** avec un prix modifié de **{prix}** l'unité."
            )
        except discord.Forbidden:
            pass

        embed = self.original_embed
        embed.color = discord.Color.orange()
        embed.add_field(
            name="Statut",
            value=f"Accepté avec modification par {interaction.user.mention} (Nouveau Prix : {prix})",
            inline=False,
        )
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            f"Demande acceptée avec le nouveau prix ({prix}) et joueur prévenu en MP !", ephemeral=True
        )


# --- CLASSE BOUTON RÉCOMPENSE / VENTE ---
class RecompenseView(discord.ui.View):
    def __init__(self, raison: str, montant: int = None, objet: str = None, member: discord.Member = None, prix: str = None):
        super().__init__(timeout=None)
        self.raison = raison
        self.montant = montant
        self.objet = objet
        self.member = member
        self.prix = prix
        self.claimed = False

    @discord.ui.button(label="🎁 Récupérer la récompense", style=discord.ButtonStyle.green, custom_id="claim_recompense")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            await interaction.response.send_message("❌ Cette récompense a déjà été récupérée !", ephemeral=True)
            return

        self.claimed = True
        button.disabled = True
        button.label = "Récompense récupérée"
        button.style = discord.ButtonStyle.grey
        await interaction.message.edit(view=self)

        details = f"📜 **Raison :** {self.raison}"
        if self.montant is not None:
            details += f"\n🪙 **Montant :** {self.montant} pièce(s)"
        if self.objet is not None:
            details += f"\n🎁 **Objet :** {self.objet}"

        await interaction.response.send_message(f"🎉 Tu as récupéré avec succès :\n{details}", ephemeral=True)

        channel = interaction.guild.get_channel(1548601473053761577)
        if channel is None:
            channel = interaction.channel

        annonce = f"🏆 **{interaction.user.mention}** a récupéré la récompense !\n📜 **Raison :** {self.raison}"
        if self.montant is not None:
            annonce += f"\n🪙 **Montant :** {self.montant} pièce(s)"
        if self.objet is not None:
            annonce += f"\n🎁 **Objet :** {self.objet}"

        await channel.send(annonce)

    @discord.ui.button(label="Valider", style=discord.ButtonStyle.green, custom_id="validate_sale")
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.member:
            await interaction.response.send_message("Ce bouton ne s'applique pas ici.", ephemeral=True)
            return

        try:
            await self.member.send(
                f"✅ Votre demande de vente de **{self.montant} {self.objet}** au prix de **{self.prix}** l'unité a été **acceptée** !"
            )
        except discord.Forbidden:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(
            name="Statut",
            value=f"Validé par {interaction.user.mention}",
            inline=False,
        )
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            "Demande validée avec succès et joueur prévenu en MP !", ephemeral=True
        )

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.red, custom_id="refuse_sale")
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.member:
            await interaction.response.send_message("Ce bouton ne s'applique pas ici.", ephemeral=True)
            return

        try:
            await self.member.send(
                f"❌ Votre demande de vente de **{self.montant} {self.objet}** au prix de **{self.prix}** l'unité a été **refusée**."
            )
        except discord.Forbidden:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(
            name="Statut", value=f"Refusé par {interaction.user.mention}", inline=False
        )
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            "La demande a été refusée et le joueur a été prévenu en MP.",
            ephemeral=True,
        )

    @discord.ui.button(label="Modifier le prix", style=discord.ButtonStyle.blurple, custom_id="modify_price")
    async def modify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.member:
            await interaction.response.send_message("Ce bouton ne s'applique pas ici.", ephemeral=True)
            return
        
        modal = PriceModal(self.member, self.objet, self.montant, interaction.message.embeds[0])
        await interaction.response.send_modal(modal)


# --- COMMANDE /CLEAR ---
@bot.tree.command(name="clear", description="Supprime un nombre spécifique de messages")
@discord.app_commands.describe(nombre="Nombre de messages à supprimer (1 à 100)")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int):
    if nombre < 1 or nombre > 100:
        await interaction.response.send_message("Le nombre doit être entre 1 et 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"✅ {len(deleted)} message(s) supprimé(s).", ephemeral=True)


# --- COMMANDE /ENVOYER_ARGENT ---
@bot.tree.command(name="envoyer_argent", description="Crée un message avec un bouton pour distribuer une récompense")
@discord.app_commands.describe(raison="La raison", montant="Montant pièces", objet="Objet")
async def envoyer_argent(interaction: discord.Interaction, raison: str, montant: int = None, objet: str = None):
    texte = f"🎁 **Nouvelle distribution disponible !**\n📜 **Raison :** {raison}"
    if montant is not None:
        texte += f"\n🪙 **Montant :** {montant} pièce(s)"
    if objet is not None:
        texte += f"\n📦 **Objet :** {objet}"
    texte += f"\n\n*Clique sur le bouton ci-dessous pour tout récupérer !*"

    view = RecompenseView(raison, montant, objet)
    await interaction.response.send_message(texte, view=view)


# ==========================================
# --- SYSTÈME DE WARNS (AJOUT & SUPPRESSION) ---
# ==========================================

@bot.tree.command(name="add_warn", description="Ajoute un avertissement à un membre et envoie une log")
@discord.app_commands.describe(membre="Le membre à avertir", raison="La raison du warn")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def add_warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    await interaction.response.defer(ephemeral=True)
    
    warns = charger_warns()
    user_id_str = str(membre.id)
    
    if user_id_str not in warns:
        warns[user_id_str] = []
        
    warn_id = len(warns[user_id_str]) + 1
    
    warn_data = {
        "id": warn_id,
        "raison": raison,
        "moderateur_id": interaction.user.id
    }
    
    warns[user_id_str].append(warn_data)
    sauvegarder_warns(warns)
    
    salon_logs = interaction.guild.get_channel(ID_SALON_LOGS_WARNS)
    if salon_logs:
        embed = discord.Embed(title="⚠️ Nouveau Warn", color=discord.Color.orange())
        embed.add_field(name="Membre", value=f"{membre.mention} (`{membre.id}`)", inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=False)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.add_field(name="ID du Warn", value=f"#{warn_id} (Total : {len(warns[user_id_str])})", inline=False)
        await salon_logs.send(embed=embed)
        
    try:
        await membre.send(f"⚠️ Vous avez reçu un avertissement sur le serveur **{interaction.guild.name}**.\n📜 **Raison :** {raison}")
    except discord.Forbidden:
        pass

    await interaction.followup.send(f"✅ Le warn n°{warn_id} a été attribué à {membre.mention} avec succès.", ephemeral=True)


@bot.tree.command(name="delete_warn", description="Supprime un avertissement spécifique d'un membre")
@discord.app_commands.describe(membre="Le membre concerné", warn_id="L'ID numérique du warn à supprimer")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def delete_warn(interaction: discord.Interaction, membre: discord.Member, warn_id: int):
    await interaction.response.defer(ephemeral=True)
    
    warns = charger_warns()
    user_id_str = str(membre.id)
    
    if user_id_str not in warns or not warns[user_id_str]:
        await interaction.followup.send(f"❌ Ce membre n'a aucun avertissement enregistré.", ephemeral=True)
        return
        
    warn_a_supprimer = None
    for w in warns[user_id_str]:
        if w["id"] == warn_id:
            warn_a_supprimer = w
            break
            
    if not warn_a_supprimer:
        await interaction.followup.send(f"❌ Aucun warn avec l'ID **#{warn_id}** n'a été trouvé pour {membre.mention}.", ephemeral=True)
        return
        
    warns[user_id_str].remove(warn_a_supprimer)
    sauvegarder_warns(warns)
    
    salon_logs = interaction.guild.get_channel(ID_SALON_LOGS_WARNS)
    if salon_logs:
        embed = discord.Embed(title="🗑️ Warn Supprimé", color=discord.Color.red())
        embed.add_field(name="Membre", value=f"{membre.mention} (`{membre.id}`)", inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=False)
        embed.add_field(name="Warn supprimé", value=f"ID #{warn_id} - Raison initiale : {warn_a_supprimer['raison']}", inline=False)
        await salon_logs.send(embed=embed)

    await interaction.followup.send(f"🗑️ Le warn **#{warn_id}** de {membre.mention} a été supprimé avec succès.", ephemeral=True)


# ==========================================
# --- SYSTÈME DE GESTION DES TRIBUS ---
# ==========================================

@bot.tree.command(name="create_tribu", description="Crée une nouvelle tribu et son salon privé")
@discord.app_commands.describe(nom="Nom de la tribu", chef="Le membre chef de la tribu", couleur="Choisis la couleur")
@discord.app_commands.choices(couleur=[
    discord.app_commands.Choice(name="Rouge", value="rouge"),
    discord.app_commands.Choice(name="Bleu", value="bleu"),
    discord.app_commands.Choice(name="Vert", value="vert"),
    discord.app_commands.Choice(name="Jaune", value="jaune"),
    discord.app_commands.Choice(name="Cyan", value="cyan"),
    discord.app_commands.Choice(name="Magenta", value="magenta"),
])
async def create_tribu(interaction: discord.Interaction, nom: str, chef: discord.Member, couleur: discord.app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)

    try:
        tribus = charger_tribus()
        nom_lower = nom.lower()

        if nom_lower in tribus:
            await interaction.followup.send(f"❌ Une tribu portant le nom **{nom}** existe déjà !", ephemeral=True)
            return

        couleur_valeur = couleur.value
        codes_ansi = {
            "rouge": "31",
            "bleu": "34",
            "vert": "32",
            "jaune": "33",
            "cyan": "36",
            "magenta": "35"
        }
        code = codes_ansi.get(couleur_valeur, "37")

        guild = interaction.guild
        
        categorie = guild.get_channel(ID_CATEGORIE_TRIBUS)
        if categorie and not isinstance(categorie, discord.CategoryChannel):
            categorie = None

        role_admin = guild.get_role(ID_ROLE_ADMIN)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            chef: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        if role_admin:
            overwrites[role_admin] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        nom_salon = f"tribu-{nom.lower().replace(' ', '-')}"
        
        salon = await guild.create_text_channel(
            name=nom_salon,
            category=categorie,
            overwrites=overwrites,
            topic=f"Salon privé de la tribu {nom}"
        )

        tribus[nom_lower] = {
            "nom_reel": nom,
            "chef_id": chef.id,
            "chef_nom": chef.display_name,
            "couleur": couleur_valeur,
            "membres": [chef.id],
            "salon_id": salon.id
        }
        sauvegarder_tribus(tribus)

        message_colore = f"```ansi\n\u001b[{code}mBienvenue dans le salon officiel de la tribu {nom} !\nChef : @{chef.display_name}\nCouleur : {couleur_valeur}\n\u001b[0m```"
        await salon.send(message_colore)
        
        await interaction.followup.send(f"✅ La tribu **{nom}** a été créée avec succès et son salon privé {salon.mention} a été généré !", ephemeral=True)

    except Exception as e:
        print(f"Erreur dans create_tribu : {e}")
        await interaction.followup.send(f"❌ Une erreur interne est survenue : `{e}`", ephemeral=True)


@bot.tree.command(name="delete_tribu", description="Supprime une tribu et son salon")
@discord.app_commands.describe(nom="Nom de la tribu à supprimer")
@discord.app_commands.checks.has_permissions(administrator=True)
async def delete_tribu(interaction: discord.Interaction, nom: str):
    await interaction.response.defer(ephemeral=True)
    tribus = charger_tribus()
    nom_lower = nom.lower()

    if nom_lower not in tribus:
        await interaction.followup.send(f"❌ Aucune tribu trouvée sous le nom de **{nom}**.", ephemeral=True)
        return

    data = tribus[nom_lower]
    if "salon_id" in data:
        salon = interaction.guild.get_channel(data["salon_id"])
        if salon:
            try:
                await salon.delete()
            except:
                pass

    del tribus[nom_lower]
    sauvegarder_tribus(tribus)
    await interaction.followup.send(f"🗑️ La tribu **{nom}** et son salon ont été supprimés avec succès.", ephemeral=True)


@bot.tree.command(name="add_membre_tribu", description="Ajoute un membre à une tribu et à son salon")
@discord.app_commands.describe(nom="Nom de la tribu", membre="Le membre à ajouter")
async def add_membre_tribu(interaction: discord.Interaction, nom: str, membre: discord.Member):
    await interaction.response.defer(ephemeral=True)
    tribus = charger_tribus()
    nom_lower = nom.lower()

    if nom_lower not in tribus:
        await interaction.followup.send(f"❌ La tribu **{nom}** n'existe pas.", ephemeral=True)
        return

    if membre.id in tribus[nom_lower]["membres"]:
        await interaction.followup.send(f"⚠️ {membre.mention} fait déjà partie de cette tribu !", ephemeral=True)
        return

    tribus[nom_lower]["membres"].append(membre.id)
    sauvegarder_tribus(tribus)

    if "salon_id" in tribus[nom_lower]:
        salon = interaction.guild.get_channel(tribus[nom_lower]["salon_id"])
        if salon:
            try:
                await salon.set_permissions(membre, read_messages=True, send_messages=True)
                await salon.send(f"➕ {membre.mention} a rejoint la tribu et a accès à ce salon !")
            except:
                pass

    await interaction.followup.send(f"✅ {membre.mention} a été ajouté à la tribu **{tribus[nom_lower]['nom_reel']}** !", ephemeral=True)


@bot.tree.command(name="delete_membre_tribu", description="Retire un membre d'une tribu et de son salon")
@discord.app_commands.describe(nom="Nom de la tribu", membre="Le membre à retirer")
async def delete_membre_tribu(interaction: discord.Interaction, nom: str, membre: discord.Member):
    await interaction.response.defer(ephemeral=True)
    tribus = charger_tribus()
    nom_lower = nom.lower()

    if nom_lower not in tribus:
        await interaction.followup.send(f"❌ La tribu **{nom}** n'existe pas.", ephemeral=True)
        return

    if membre.id not in tribus[nom_lower]["membres"]:
        await interaction.followup.send(f"⚠️ {membre.mention} ne fait pas partie de cette tribu.", ephemeral=True)
        return

    if membre.id == tribus[nom_lower]["chef_id"]:
        await interaction.followup.send(f"❌ Tu ne peux pas retirer le chef de sa propre tribu !", ephemeral=True)
        return

    tribus[nom_lower]["membres"].remove(membre.id)
    sauvegarder_tribus(tribus)

    if "salon_id" in tribus[nom_lower]:
        salon = interaction.guild.get_channel(tribus[nom_lower]["salon_id"])
        if salon:
            try:
                await salon.set_permissions(membre, overwrite=None)
                await salon.send(f"➖ {membre.mention} a quitté ou a été retiré de la tribu.")
            except:
                pass

    await interaction.followup.send(f"🗑️ {membre.mention} a été retiré de la tribu **{tribus[nom_lower]['nom_reel']}**.", ephemeral=True)


@bot.tree.command(name="user_tribu", description="Affiche toutes les tribus, leurs chefs et leurs membres")
async def user_tribu(interaction: discord.Interaction):
    tribus = charger_tribus()
    if not tribus:
        await interaction.response.send_message("📂 Aucune tribu n'a été créée pour le moment.", ephemeral=True)
        return

    description = ""
    for cle, data in tribus.items():
        membres_mentions = [f"<@{m_id}>" for m_id in data["membres"]]
        salon_mention = f"<#{data['salon_id']}>" if "salon_id" in data else "Aucun"
        description += f"🏰 **{data['nom_reel']}** (Salon : {salon_mention})\n"
        description += f"👑 **Chef :** <@{data['chef_id']}>\n"
        description += f"🎨 **Couleur :** {data['couleur']}\n"
        description += f"👥 **Membres ({len(data['membres'])}) :** {', '.join(membres_mentions)}\n\n"

    embed = discord.Embed(title="📜 Liste de toutes les tribus", description=description, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="info_my_tribu", description="Donne les informations de ta propre tribu")
async def info_my_tribu(interaction: discord.Interaction):
    tribus = charger_tribus()
    tribu_trouvee = None

    for cle, data in tribus.items():
        if interaction.user.id in data["membres"]:
            tribu_trouvee = data
            break

    if not tribu_trouvee:
        await interaction.response.send_message("❌ Tu ne fais partie d'aucune tribu.", ephemeral=True)
        return

    membres_mentions = [f"<@{m_id}>" for m_id in tribu_trouvee["membres"]]
    salon_mention = f"<#{tribu_trouvee['salon_id']}>" if "salon_id" in tribu_trouvee else "Aucun"
    
    embed = discord.Embed(title=f"🛡️ Ta Tribu : {tribu_trouvee['nom_reel']}", color=discord.Color.green())
    embed.add_field(name="👑 Chef", value=f"<@{tribu_trouvee['chef_id']}>", inline=False)
    embed.add_field(name="🎨 Couleur d'écriture", value=tribu_trouvee['couleur'], inline=False)
    embed.add_field(name="💬 Salon privé", value=salon_mention, inline=False)
    embed.add_field(name="👥 Membres", value=", ".join(membres_mentions), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="info_tribu", description="Affiche les infos d'une tribu spécifique")
@discord.app_commands.describe(nom="Nom de la tribu")
async def info_tribu(interaction: discord.Interaction, nom: str):
    tribus = charger_tribus()
    nom_lower = nom.lower()

    if nom_lower not in tribus:
        await interaction.response.send_message(f"❌ La tribu **{nom}** est introuvable.", ephemeral=True)
        return

    data = tribus[nom_lower]
    membres_mentions = [f"<@{m_id}>" for m_id in data["membres"]]
    salon_mention = f"<#{data['salon_id']}>" if "salon_id" in data else "Aucun"

    embed = discord.Embed(title=f"🛡️ Tribu : {data['nom_reel']}", color=discord.Color.gold())
    embed.add_field(name="👑 Chef", value=f"<@{data['chef_id']}>", inline=False)
    embed.add_field(name="🎨 Couleur", value=data['couleur'], inline=False)
    embed.add_field(name="💬 Salon privé", value=salon_mention, inline=False)
    embed.add_field(name="👥 Membres", value=", ".join(membres_mentions), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="admininfo_tribu", description="[ADMIN] Affiche un rapport complet de toutes les tribus")
@discord.app_commands.checks.has_permissions(administrator=True)
async def admininfo_tribu(interaction: discord.Interaction):
    tribus = charger_tribus()
    if not tribus:
        await interaction.response.send_message("📂 Aucune base de données de tribu trouvée.", ephemeral=True)
        return

    texte_global = ""
    for cle, data in tribus.items():
        membres_bruts = [str(m_id) for m_id in data["membres"]]
        salon_mention = f"<#{data['salon_id']}>" if "salon_id" in data else "Aucun"
        texte_global += f"🔹 **Nom :** {data['nom_reel']}\n"
        texte_global += f"👑 **ID Chef :** {data['chef_id']} ({data['chef_nom']})\n"
        texte_global += f"🎨 **Couleur :** {data['couleur']}\n"
        texte_global += f"💬 **Salon :** {salon_mention}\n"
        texte_global += f"📊 **Total membres :** {len(data['membres'])}\n"
        texte_global += f"🆔 **IDs des membres :** {', '.join(membres_bruts)}\n"
        texte_global += "-----------------------------------\n"

    embed = discord.Embed(title="🛠️ Rapport Admin - Toutes les Tribus", description=texte_global, color=discord.Color.dark_red())
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# --- LANCEMENT UNIQUE DU BOT ---
# ==========================================

if __name__ == "__main__":
    bot.run(TOKEN)