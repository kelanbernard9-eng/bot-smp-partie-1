import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import os
import asyncio
import random
import re

# ==========================================
# CONFIGURATION ET INTENTS
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# CONSTANTES ET IDS
# ==========================================
ADMIN_ROLE_ID = 1543664637546070217  
ADMIN_USER_ID = 1543664637546070217  
VERIF_ROLE_ID = 1543666646571548712  

# Salons de Logs
LOGS_ALL_ID = 1543678552875204721        
LOGS_CODES_ID = 1543669407560241152      
LOGS_SANCTION_ID = 1543670405523570808 
MONEY_LOG_CHANNEL_ID = 1546114003913408512
SHOP_SUCCESS_LOG_ID = 1548325976650420244 # Salon demandé pour les achats validés

# Salons / Catégories
VERIF_CHANNEL_ID = 1543669979088551986
SHOP_CHANNEL_ID = 154368882235986052
TICKET_CHANNEL_ID = 1543669176046985407
TICKET_CATEGORY_ID = 1543669176046985407
CODES_CHANNEL_ID = 1543668572067209366

# Mots interdits
BAD_WORDS = ["insulte1", "insulte2", "connard", "pute", "fdp", "salope"]

# Fichiers
DATA_FILE_BOUTIQUE = "boutique_data.json"
DB_FILE_MAIN = "database.json"
CONFIG_FILE = "config.json"

# ==========================================
# FONCTION DE VÉRIFICATION ADMIN STRICTE
# ==========================================
def est_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.id == ADMIN_USER_ID:
        return True
    if any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
        return True
    return False

# ==========================================
# CHARGEMENT DU TOKEN
# ==========================================
def charger_token():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
                return config.get("token") or config.get("DISCORD_TOKEN") or config.get("BOT_TOKEN")
            except json.JSONDecodeError:
                return None
    return None

# ==========================================
# GESTION DES BASES DE DONNÉES
# ==========================================

def charger_donnees_boutique():
    if os.path.exists(DATA_FILE_BOUTIQUE):
        with open(DATA_FILE_BOUTIQUE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return {
                    "objets_sell": data.get("objets_sell", []),
                    "ventes_joueurs": data.get("ventes_joueurs", [])
                }
            except json.JSONDecodeError:
                return {"objets_sell": [], "ventes_joueurs": []}
    return {"objets_sell": [], "ventes_joueurs": []}

def sauvegarder_donnees_boutique():
    data = {
        "objets_sell": OBJETS_SELL,
        "ventes_joueurs": VENTES_JOUEURS
    }
    with open(DATA_FILE_BOUTIQUE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

donnees_globales = charger_donnees_boutique()
OBJETS_SELL = donnees_globales["objets_sell"]
VENTES_JOUEURS = donnees_globales["ventes_joueurs"]

def load_data_main():
    if os.path.exists(DB_FILE_MAIN):
        with open(DB_FILE_MAIN, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return {
                    "codes": data.get("codes", {}),
                    "shop_items": data.get("shop_items", {}),
                    "user_redeemed": {int(k): v for k, v in data.get("user_redeemed", {}).items()},
                    "user_warns": {int(k): v for k, v in data.get("user_warns", {}).items()},
                    "verified_data": {int(k): v for k, v in data.get("verified_data", {}).items()},
                    "verification_progress": {int(k): v for k, v in data.get("verification_progress", {}).items()},
                    "user_money": {int(k): v for k, v in data.get("user_money", {}).items()},
                    "quiz_completed": {int(k): v for k, v in data.get("quiz_completed", {}).items()},
                    "user_messages": {int(k): v for k, v in data.get("user_messages", {}).items()},
                    "vendeur_salons": {str(k): v for k, v in data.get("vendeur_salons", {}).items()}
                }
            except Exception:
                pass
    return {"codes": {}, "shop_items": {}, "user_redeemed": {}, "user_warns": {}, "verified_data": {}, "verification_progress": {}, "user_money": {}, "quiz_completed": {}, "user_messages": {}, "vendeur_salons": {}}

def save_data_main():
    data = {
        "codes": active_codes,
        "shop_items": active_shop_items,
        "user_redeemed": user_redeemed_codes,
        "user_warns": user_warns,
        "verified_data": verified_users_data,
        "verification_progress": verification_progress,
        "user_money": user_money,
        "quiz_completed": user_quiz_completed,
        "user_messages": user_messages,
        "vendeur_salons": vendeur_salons
    }
    with open(DB_FILE_MAIN, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_data_main()
active_codes = db["codes"]
active_shop_items = db["shop_items"]
user_redeemed_codes = db["user_redeemed"]
user_warns = db["user_warns"]
verified_users_data = db["verified_data"]
verification_progress = db["verification_progress"]
user_money = db["user_money"]
user_quiz_completed = db["quiz_completed"]
user_messages = db["user_messages"]
vendeur_salons = db["vendeur_salons"]

# ==========================================
# FONCTIONS UTILITAIRES (ECONOMIE & SALONS VENDEURS)
# ==========================================

def add_money(user_id: int, amount: int):
    if user_id not in user_money:
        user_money[user_id] = 0
    user_money[user_id] += amount
    save_data_main()

def remove_money(user_id: int, amount: int):
    if user_id not in user_money:
        user_money[user_id] = 0
    user_money[user_id] = max(0, user_money[user_id] - amount)
    save_data_main()

def get_money(user_id: int) -> int:
    return user_money.get(user_id, 0)

async def get_or_create_vendeur_salon(guild: discord.Guild, vendeur_nom: str) -> discord.TextChannel:
    """Crée ou récupère le salon permanent dédié à un vendeur pour gérer ses commandes."""
    global vendeur_salons
    
    chan_id = vendeur_salons.get(vendeur_nom.lower())
    if chan_id:
        channel = guild.get_channel(int(chan_id))
        if channel:
            return channel

    category = guild.get_channel(TICKET_CATEGORY_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    
    vendeur_member = discord.utils.find(lambda m: m.name.lower() == vendeur_nom.lower() or (m.display_name and m.display_name.lower() == vendeur_nom.lower()), guild.members)
    if vendeur_member:
        overwrites[vendeur_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    admin_role = guild.get_role(ADMIN_ROLE_ID)
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    new_channel = await guild.create_text_channel(
        name=f"vendeur-{vendeur_nom}".lower(),
        category=category if isinstance(category, discord.CategoryChannel) else None,
        overwrites=overwrites
    )
    
    vendeur_salons[vendeur_nom.lower()] = new_channel.id
    save_data_main()
    
    embed = discord.Embed(
        title=f"📦 Salon de gestion des commandes : {vendeur_nom}",
        description="Ce salon est ton espace permanent. Toutes les commandes et demandes d'achats concernant tes objets y seront répertoriées pour que tu puisses valider les remises en jeu.",
        color=discord.Color.blue()
    )
    await new_channel.send(embed=embed)
    return new_channel

def get_shop_embed():
    embed = discord.Embed(
        title="🛒 CATALOGUE DE LA BOUTIQUE",
        description="Voici l'ensemble des tableaux d'achats et de ventes disponibles :",
        color=discord.Color.gold()
    )
    
    if not active_shop_items:
        embed.add_field(name="Vide", value="Aucun article disponible pour le moment.", inline=False)
        embed.set_footer(text="Clique sur le bouton ci-dessous pour passer commande !")
        return embed

    buy_items = {}
    sell_items = {}
    
    for name, data in active_shop_items.items():
        item_type = data.get("type", "Achat").lower()
        if item_type == "vente":
            sell_items[name] = data
        else:
            buy_items[name] = data

    buy_text = ""
    if not buy_items:
        buy_text = "*Aucun article en achat.*"
    else:
        for item_name, data in buy_items.items():
            price = data.get("price", 0)
            reward = data.get("reward", "Non spécifié")
            max_stock = data.get("max_stock")
            sold = data.get("sold", 0)
            
            stock_info = f"{sold}/{max_stock} vendus" if max_stock is not None else f"{sold} vendus (Illimité)"
            if max_stock is not None and sold >= max_stock:
                stock_info += " 🔴"
                
            buy_text += f"📦 **{item_name}**\n> 🎁 Récompense : {reward}\n> 💰 Prix : {price} pièces | 📊 Stock : {stock_info}\n\n"

    embed.add_field(name="🛍️ TABLEAU DES ACHATS", value=buy_text, inline=False)

    sell_text = ""
    if not sell_items:
        sell_text = "*Aucun article en vente.*"
    else:
        for item_name, data in sell_items.items():
            price = data.get("price", 0)
            reward = data.get("reward", "Non spécifié")
            max_stock = data.get("max_stock")
            sold = data.get("sold", 0)
            
            stock_info = f"{sold}/{max_stock} vendus" if max_stock is not None else f"{sold} vendus (Illimité)"
            if max_stock is not None and sold >= max_stock:
                stock_info += " 🔴"
                
            sell_text += f"🏷️ **{item_name}**\n> 🎁 Contrepartie : {reward}\n> 💰 Gain : {price} pièces | 📊 Stock : {stock_info}\n\n"

    embed.add_field(name="💰 TABLEAU DES VENTES", value=sell_text, inline=False)
    embed.set_footer(text="Clique sur le bouton ci-dessous pour interagir avec la boutique !")
    return embed

# ==========================================
# CLASSES : BOUTIQUE JOUEURS & UI
# ==========================================

class ModifQuantiteModal(Modal, title="Modifier la quantité"):
    nouvelle_quantite = TextInput(label="Nouvelle quantité en stock", placeholder="Ex: 3")

    def __init__(self, vente_data, index, view_parent):
        super().__init__()
        self.vente_data = vente_data
        self.index = index
        self.view_parent = view_parent

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_qty = int(self.nouvelle_quantite.value)
        except ValueError:
            return await interaction.response.send_message("❌ La quantité doit être un nombre valide.", ephemeral=True)
        
        self.vente_data['nombre'] = new_qty
        sauvegarder_donnees_boutique()
        await interaction.response.send_message(f"✅ Quantité mise à jour : **{new_qty}**", ephemeral=True)


class ConfirmPaymentDoneView(View):
    def __init__(self, vendeur_nom, prix_total, index_vente, acheteur_mention=None, acheteur_id=None, objet_nom=None, quantite=None):
        super().__init__(timeout=None)
        self.vendeur_nom = vendeur_nom
        self.prix_total = prix_total
        self.index_vente = index_vente
        self.acheteur_mention = acheteur_mention
        self.acheteur_id = acheteur_id
        self.objet_nom = objet_nom
        self.quantite = quantite

    @discord.ui.button(label="L'objet a bien été remis en jeu, valider", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_done(self, interaction: discord.Interaction, button: Button):
        global VENTES_JOUEURS
        
        is_adm = est_admin(interaction)
        is_vendeur = interaction.user.name.lower() == self.vendeur_nom.lower()

        if not (is_adm or is_vendeur):
            return await interaction.response.send_message("❌ Seul le vendeur peut confirmer qu'il a remis l'objet en jeu !", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        objet_nom = self.objet_nom or "l'objet"
        quantite_val = self.quantite or "1"
        
        if 0 <= self.index_vente < len(VENTES_JOUEURS):
            objet_vendu = VENTES_JOUEURS.pop(self.index_vente)
            objet_nom = objet_vendu['objet']
            quantite_val = objet_vendu['nombre']
            sauvegarder_donnees_boutique()

        success_channel = interaction.guild.get_channel(SHOP_SUCCESS_LOG_ID)
        if success_channel:
            user_data = verified_users_data.get(self.acheteur_id, {"psn": "Inconnu", "mc": "Inconnu", "age": "Inconnu", "surnom": "Inconnu"})
            embed_success = discord.Embed(
                title="🎉 TRANSACTION TERMINÉE & VALIDÉE",
                description=(
                    f"• **Acheteur :** {self.acheteur_mention} (`ID: {self.acheteur_id}`)\n"
                    f"• **Vendeur :** {self.vendeur_nom}\n"
                    f"• **Objet :** {objet_nom} (x{quantite_val})\n"
                    f"• **Montant payé :** {self.prix_total} pièces\n\n"
                    f"📋 **Infos de l'acheteur :**\n"
                    f"• **PSN :** {user_data.get('psn')}\n"
                    f"• **Minecraft :** {user_data.get('mc')}\n"
                    f"• **Âge :** {user_data.get('age')}\n"
                    f"• **Surnom :** {user_data.get('surnom')}\n\n"
                    f"👑 **Validé par :** {interaction.user.mention}"
                ),
                color=discord.Color.green()
            )
            view_double = DoubleValidateLogView(self.vendeur_nom, self.prix_total, objet_nom, self.acheteur_id)
            await success_channel.send(embed=embed_success, view=view_double)

        await interaction.response.send_message(
            f"🎉 **Transaction confirmée et finalisée par le vendeur !**\n"
            f"📦 L'objet **{objet_nom}** a été retiré de la boutique et archivé dans les logs de succès.",
            ephemeral=False
        )


class DoubleValidateLogView(View):
    def __init__(self, vendeur_nom, prix_total, objet_nom, acheteur_id):
        super().__init__(timeout=None)
        self.vendeur_nom = vendeur_nom
        self.prix_total = prix_total
        self.objet_nom = objet_nom
        self.acheteur_id = acheteur_id

    @discord.ui.button(label="Double Validation Admin OK", style=discord.ButtonStyle.blurple, emoji="🛡️")
    async def double_validate(self, interaction: discord.Interaction, button: Button):
        if not est_admin(interaction):
            return await interaction.response.send_message("❌ Réservé aux administrateurs pour la double validation.", ephemeral=True)
        
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"🛡️ **Double validation effectuée par l'admin {interaction.user.mention}**. Transaction scellée sans litige.", ephemeral=False)


class PaymentActionView(View):
    def __init__(self, vendeur_nom, prix_total, index_vente, acheteur_id, acheteur_mention, objet_nom, quantite):
        super().__init__(timeout=None)
        self.vendeur_nom = vendeur_nom
        self.prix_total = prix_total
        self.index_vente = index_vente
        self.acheteur_id = acheteur_id
        self.acheteur_mention = acheteur_mention
        self.objet_nom = objet_nom
        self.quantite = quantite

    @discord.ui.button(label="Acheter / Payer avec mon solde", style=discord.ButtonStyle.blurple, emoji="💳")
    async def acheter_callback(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.acheteur_id and not est_admin(interaction):
            return await interaction.response.send_message("❌ Seul l'acheteur concerné par ce ticket peut effectuer le paiement !", ephemeral=True)

        solde_acheteur = get_money(self.acheteur_id)
        try:
            prix_int = int(self.prix_total)
        except ValueError:
            prix_int = 0

        if solde_acheteur < prix_int:
            return await interaction.response.send_message(
                f"❌ **Paiement refusé !** Tu n'as pas assez d'argent.\n"
                f"• Ton solde : **{solde_acheteur} pièces**\n"
                f"• Prix requis : **{prix_int} pièces**",
                ephemeral=True
            )

        guild = interaction.guild
        vendeur_member = discord.utils.get(guild.members, name=self.vendeur_nom)
        if not vendeur_member:
            vendeur_member = discord.utils.find(lambda m: m.name.lower() == self.vendeur_nom.lower() or (m.display_name and m.display_name.lower() == self.vendeur_nom.lower()), guild.members)

        if not vendeur_member:
            return await interaction.response.send_message(
                f"❌ Erreur : Impossible de trouver le compte Discord du vendeur (**{self.vendeur_nom}**) sur le serveur pour lui verser l'argent.",
                ephemeral=True
            )

        remove_money(self.acheteur_id, prix_int)
        add_money(vendeur_member.id, prix_int)
        nouveau_solde_acheteur = get_money(self.acheteur_id)

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        view_confirmation = ConfirmPaymentDoneView(self.vendeur_nom, self.prix_total, self.index_vente, self.acheteur_mention, self.acheteur_id, self.objet_nom, self.quantite)
        
        await interaction.response.send_message(
            f"✅ **Paiement réussi par {interaction.user.mention} !**\n"
            f"• **{prix_int} pièces** ont été retirées de ton compte (Nouveau solde : {nouveau_solde_acheteur} pièces).\n"
            f"• L'argent a été versé au vendeur (**{self.vendeur_nom}**).\n\n"
            f"🔒 *Il ne reste plus qu'à ce que le vendeur (**{self.vendeur_nom}**) donne l'objet en jeu et clique sur le bouton de validation finale.*",
            view=view_confirmation,
            ephemeral=False
        )


class TicketControlView(View):
    def __init__(self, vendeur_nom, vente_data, index_vente, acheteur_mention, acheteur_id):
        super().__init__(timeout=None)
        self.vendeur_nom = vendeur_nom
        self.vente_data = vente_data
        self.index_vente = index_vente
        self.acheteur_mention = acheteur_mention
        self.acheteur_id = acheteur_id

    @discord.ui.button(label="Lancer la procédure de paiement", style=discord.ButtonStyle.green)
    async def ask_payment(self, interaction: discord.Interaction, button: Button):
        is_adm = est_admin(interaction)
        is_vendeur = interaction.user.name.lower() == self.vendeur_nom.lower()

        if not (is_adm or is_vendeur):
            return await interaction.response.send_message("❌ Seul le vendeur ou un administrateur peut lancer la procédure de paiement.", ephemeral=True)
        
        prix_total = self.vente_data['prix']
        if self.vente_data.get('type_prix') == 'Unité':
            try:
                prix_total = str(int(self.vente_data['prix']) * int(self.vente_data['nombre']))
            except ValueError:
                pass

        content = (
            f"📢 **Demande de paiement lancée !**\n"
            f"• **Acheteur :** {self.acheteur_mention}\n"
            f"• **Vendeur :** {self.vendeur_nom}\n"
            f"• **Objet :** {self.vente_data['objet']}\n"
            f"• **Quantité :** {self.vente_data['nombre']}\n"
            f"• **Prix Total :** **{prix_total} pièces**"
        )
        
        view = PaymentActionView(self.vendeur_nom, prix_total, self.index_vente, self.acheteur_id, self.acheteur_mention, self.vente_data['objet'], self.vente_data['nombre'])
        await interaction.channel.send(content=content, view=view)
        await interaction.response.send_message("✅ Étape de paiement initialisée dans le salon.", ephemeral=True)

    @discord.ui.button(label="Modifier la quantité", style=discord.ButtonStyle.grey)
    async def modify_qty(self, interaction: discord.Interaction, button: Button):
        if interaction.user.name.lower() != self.vendeur_nom.lower() and not est_admin(interaction):
            return await interaction.response.send_message("❌ Seul le vendeur ou un admin peut modifier la quantité.", ephemeral=True)
        await interaction.response.send_modal(ModifQuantiteModal(self.vente_data, self.index_vente, self))

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        is_adm = est_admin(interaction)
        is_vendeur = interaction.user.name.lower() == self.vendeur_nom.lower()

        if is_adm or is_vendeur:
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Le membre créateur ne peut pas fermer le ticket. Seul le vendeur ou un admin le peut.", ephemeral=True)


class BoutiqueSelect(Select):
    def __init__(self):
        options = []
        for index, vente in enumerate(VENTES_JOUEURS):
            prix_affichage = vente['prix']
            if vente.get('type_prix') == 'Unité':
                prix_affichage += " /unité"
            label = f"{vente['objet']} (x{vente['nombre']}) - {prix_affichage}"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    description=f"Vendeur : {vente['joueur']}",
                    value=str(index)
                )
            )
        
        if not options:
            options.append(discord.SelectOption(label="Aucune vente disponible", value="none"))

        super().__init__(placeholder="🛒 Choisir un objet à acheter...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("❌ Aucun objet n'est disponible à l'achat.", ephemeral=True)
        
        index = int(self.values[0])
        vente = VENTES_JOUEURS[index]
        
        modal = AcheterQuantiteModal(vente, index)
        await interaction.response.send_modal(modal)


class AcheterQuantiteModal(Modal, title="Quantité souhaitée"):
    def __init__(self, vente_data, index):
        super().__init__()
        self.vente_data = vente_data
        self.index = index
        self.quantite_input = TextInput(
            label=f"Quantité (Max disponible : {vente_data['nombre']})",
            placeholder=f"Entre 1 et {vente_data['nombre']}...",
            default="1",
            required=True
        )
        self.add_item(self.quantite_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            q_demandee = int(self.quantite_input.value)
        except ValueError:
            return await interaction.response.send_message("❌ Veuillez entrer un nombre valide.", ephemeral=True)

        stock_max = int(self.vente_data['nombre'])
        
        if q_demandee <= 0:
            return await interaction.response.send_message("❌ La quantité doit être supérieure à 0.", ephemeral=True)
        
        if q_demandee > stock_max:
            return await interaction.response.send_message(
                f"❌ **Quantité impossible !** Il n'y a que **{stock_max}** exemplaire(s) en stock pour cet objet.",
                ephemeral=True
            )

        vente_copie = self.vente_data.copy()
        vente_copie['nombre'] = q_demandee

        guild = interaction.guild
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        vendeur_member = discord.utils.get(guild.members, name=vente_copie['joueur'])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=False),
        }
        if vendeur_member:
            overwrites[vendeur_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{vente_copie['objet']}-{interaction.user.name}".lower(),
            overwrites=overwrites
        )

        prix_str = f"{vente_copie['prix']} ({vente_copie.get('type_prix', 'Total')})"
        embed = discord.Embed(
            title="🛒 Transaction en cours",
            description=f"Acheteur : {interaction.user.mention}\nVendeur : {vente_copie['joueur']}\nObjet : **{vente_copie['objet']}**\nQuantité commandée : **{q_demandee}** / {stock_max}\nPrix : {prix_str}",
            color=discord.Color.green()
        )
        
        view = TicketControlView(vente_copie['joueur'], vente_copie, self.index, interaction.user.mention, interaction.user.id)
        await ticket_channel.send(embed=embed, view=view)
        
        vendeur_salon = await get_or_create_vendeur_salon(guild, vente_copie['joueur'])
        if vendeur_salon and vendeur_salon.id != ticket_channel.id:
            user_data = verified_users_data.get(interaction.user.id, {"psn": "Inconnu", "mc": "Inconnu"})
            embed_vendeur_salon = discord.Embed(
                title="📥 Nouvelle commande reçue sur ton article !",
                description=(
                    f"• **Acheteur :** {interaction.user.mention} (`{interaction.user.name}`)\n"
                    f"• **Objet :** {vente_copie['objet']}\n"
                    f"• **Quantité demandée :** {q_demandee}\n"
                    f"• **Prix :** {prix_str}\n"
                    f"• **Salon de discussion dédié :** {ticket_channel.mention}\n\n"
                    f"*(Prépare l'objet en jeu et procède à la validation une fois le paiement effectué !)*"
                ),
                color=discord.Color.gold()
            )
            await vendeur_salon.send(embed=embed_vendeur_salon)

        await interaction.response.send_message(f"✅ Ticket créé avec succès : {ticket_channel.mention}", ephemeral=True)


class BoutiqueTableView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BoutiqueSelect())


class SelectDeleteDirectSelect(Select):
    def __init__(self, user_sales_with_index):
        options = []
        for index, vente in user_sales_with_index:
            label = f"{vente['objet']} (x{vente['nombre']}) - {vente['prix']}"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=str(index)
                )
            )
        super().__init__(placeholder="🗑️ Choisis l'objet à supprimer...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global VENTES_JOUEURS
        index_choisi = int(self.values[0])
        
        if 0 <= index_choisi < len(VENTES_JOUEURS):
            objet_supprime = VENTES_JOUEURS.pop(index_choisi)
            sauvegarder_donnees_boutique()
            await interaction.response.send_message(f"✅ L'objet **{objet_supprime['objet']}** (x{objet_supprime['nombre']}) a été supprimé de tes ventes avec succès !", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ L'objet n'a pas été trouvé ou a déjà été supprimé.", ephemeral=True)
        
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)


class SelectDeleteDirectView(View):
    def __init__(self, user_sales_with_index):
        super().__init__(timeout=None)
        self.add_item(SelectDeleteDirectSelect(user_sales_with_index))


class AdminTicketView(View):
    def __init__(self, data):
        super().__init__(timeout=None)
        self.data = data

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not est_admin(interaction):
            await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser ces boutons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Valider", style=discord.ButtonStyle.green)
    async def valider_callback(self, interaction: discord.Interaction, button: Button):
        salon = interaction.guild.get_channel(LOGS_ALL_ID)
        
        embed = discord.Embed(title="🛒 Nouvelle offre de vente joueur validée", color=discord.Color.green())
        embed.add_field(name="Joueur", value=self.data['joueur'], inline=True)
        embed.add_field(name="Objet", value=self.data['objet'], inline=True)
        embed.add_field(name="Quantité", value=str(self.data['nombre']), inline=True)
        embed.add_field(name="Prix", value=f"{self.data['prix']} ({self.data['type_prix']})", inline=True)
        
        if salon:
            await salon.send(embed=embed)
        
        VENTES_JOUEURS.append(self.data)
        sauvegarder_donnees_boutique()
        
        vendeur_salon = await get_or_create_vendeur_salon(interaction.guild, self.data['joueur'])
        if vendeur_salon:
            embed_vendeur = discord.Embed(
                title="🏷️ Nouvel objet mis en vente dans la boutique !",
                description=f"• **Objet :** {self.data['objet']}\n• **Quantité :** {self.data['nombre']}\n• **Prix :** {self.data['prix']} ({self.data['type_prix']})\n\n*(Ce salon est ton espace permanent pour suivre tes commandes).*",
                color=discord.Color.green()
            )
            await vendeur_salon.send(embed=embed_vendeur)

        await interaction.response.send_message("✅ Offre validée et publiée dans le salon des ventes !", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Modifier le prix", style=discord.ButtonStyle.blurple)
    async def modifier_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ModifPrixModal(self.data, interaction.message))


class ModifPrixModal(Modal, title="Modifier le prix de l'offre"):
    nouveau_prix = TextInput(label="Nouveau prix", placeholder="Entre le nouveau prix...")

    def __init__(self, data, message):
        super().__init__()
        self.data = data
        self.target_message = message

    async def on_submit(self, interaction: discord.Interaction):
        self.data['prix'] = self.children[0].value
        sauvegarder_donnees_boutique()
        await interaction.response.send_message(f"✅ Prix modifié avec succès à : **{self.children[0].value}**", ephemeral=True)
        
        embed = interaction.message.embeds[0]
        embed.set_field_at(3, name="Prix", value=f"{self.data['prix']} ({self.data.get('type_prix', 'Total')})", inline=True)
        await self.target_message.edit(embed=embed)


# ==========================================
# CLASSES : SYSTEMES PRINCIPAUX
# ==========================================

class VerificationModal(discord.ui.Modal, title="Formulaire de Vérification"):
    psn = discord.ui.TextInput(label="Votre PSN (PlayStation Network)", placeholder="Ex: MonPseudoPS5", required=True, max_length=50)
    mc = discord.ui.TextInput(label="Votre Pseudo Minecraft", placeholder="Ex: SteveDu59", required=True, max_length=50)
    age = discord.ui.TextInput(label="Votre Âge", placeholder="Ex: 14", required=True, max_length=3)
    surnom = discord.ui.TextInput(label="Votre Surnom / Prénom", placeholder="Ex: Thomas", required=True, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        verified_users_data[interaction.user.id] = {
            "psn": self.psn.value,
            "mc": self.mc.value,
            "age": self.age.value,
            "surnom": self.surnom.value
        }
        if interaction.user.id in verification_progress:
            del verification_progress[interaction.user.id]
        save_data_main()

        role = interaction.guild.get_role(VERIF_ROLE_ID)
        if role:
            try:
                await interaction.user.add_roles(role)
            except Exception:
                pass

        logs_all = bot.get_channel(LOGS_ALL_ID)
        if logs_all:
            embed = discord.Embed(
                title="✅ Nouvelle Vérification Validée",
                description=(
                    f"**Membre :** {interaction.user.mention} (`{interaction.user}`)\n\n"
                    f"• **PSN :** {self.psn.value}\n"
                    f"• **Minecraft :** {self.mc.value}\n"
                    f"• **Âge :** {self.age.value}\n"
                    f"• **Surnom :** {self.surnom.value}"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"ID Utilisateur : {interaction.user.id}")
            await logs_all.send(embed=embed)

        await interaction.response.send_message("✅ **Vérification réussie !** Ton accès au serveur est maintenant débloqué.", ephemeral=True)

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vérifier mon compte", style=discord.ButtonStyle.green, custom_id="btn_verify_main")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerificationModal())


class MessageSelectUser(discord.ui.Select):
    def __init__(self, verified_users):
        options = []
        for uid, udata in verified_users.items():
            surnom = udata.get("surnom", "Inconnu")
            mc = udata.get("mc", "Inconnu")
            options.append(discord.SelectOption(
                label=f"{surnom} (MC: {mc})",
                description=f"Envoyer un message privé via l'app",
                value=str(uid)
            ))
        super().__init__(placeholder="Choisis un utilisateur vérifié à contacter...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        recipient_id = int(self.values[0])
        if recipient_id == interaction.user.id:
            await interaction.response.send_message("❌ Tu ne peux pas t'envoyer un message à toi-même !", ephemeral=True)
            return
        await interaction.response.send_modal(SendMessageModal(recipient_id))

class SendMessageModal(discord.ui.Modal, title="Envoyer un message"):
    def __init__(self, recipient_id: int):
        super().__init__()
        self.recipient_id = recipient_id

    message_content = discord.ui.TextInput(
        label="Ton message",
        placeholder="Écris ton message ici...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        sender_id = interaction.user.id
        
        if self.recipient_id not in user_messages:
            user_messages[self.recipient_id] = []
            
        sender_info = verified_users_data.get(sender_id, {"surnom": interaction.user.name})
        sender_name = sender_info.get("surnom", interaction.user.name)

        user_messages[self.recipient_id].append({
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": self.message_content.value
        })
        save_data_main()

        await interaction.response.send_message(f"✅ Ton message a bien été envoyé à **{sender_name}** via l'application !", ephemeral=True)

class MessageAppView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.button(label="✉️ Envoyer un message", style=discord.ButtonStyle.primary, custom_id="msg_send_btn")
    async def send_msg_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas ton panneau de messagerie !", ephemeral=True)
            return
        
        verified_others = {uid: data for uid, data in verified_users_data.items() if uid != interaction.user.id}
        
        if not verified_others:
            await interaction.response.send_message("❌ Aucun autre utilisateur vérifié n'est disponible pour le moment.", ephemeral=True)
            return

        view = discord.ui.View(timeout=60)
        view.add_item(MessageSelectUser(verified_others))
        await interaction.response.send_message("📌 **Sélectionne la personne à qui envoyer un message :**", view=view, ephemeral=True)

    @discord.ui.button(label="📥 Boîte de réception", style=discord.ButtonStyle.success, custom_id="msg_inbox_btn")
    async def inbox_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas ton panneau de messagerie !", ephemeral=True)
            return

        inbox = user_messages.get(interaction.user.id, [])
        embed = discord.Embed(title="📥 Boîte de Réception (App Message)", color=discord.Color.blurple())

        if not inbox:
            embed.description = "Ta boîte de réception est vide."
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed.description = f"Tu as reçu **{len(inbox)} message(s)** :"
            for idx, msg in enumerate(inbox[-5:], 1):  
                embed.add_field(name=f"Message {idx} de {msg['sender_name']}", value=msg['content'], inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🗑️ Vider ma boîte", style=discord.ButtonStyle.danger, custom_id="msg_clear_btn")
    async def clear_inbox_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas ton panneau !", ephemeral=True)
            return
        
        if interaction.user.id in user_messages:
            user_messages[interaction.user.id] = []
            save_data_main()
            
        await interaction.response.send_message("🗑️ Ta boîte de réception a été vidée avec succès.", ephemeral=True)


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Aide en Jeu / Support", description="Besoin d'aide générale sur le serveur", emoji="🎮", value="Aide en Jeu"),
            discord.SelectOption(label="Problème Boutique", description="Un souci avec un achat ou une commande", emoji="🛒", value="Problème Boutique"),
            discord.SelectOption(label="Report / Joueur Toxique", description="Signaler un joueur ou un bug", emoji="⚠️", value="Signalement"),
            discord.SelectOption(label="Autre Demande", description="Pour toute autre raison", emoji="🎫", value="Autre")
        ]
        super().__init__(placeholder="Choisis le motif de ton ticket...", min_values=1, max_values=1, options=options, custom_id="ticket_reason_select")

    async def callback(self, interaction: discord.Interaction):
        motif = self.values[0]
        await interaction.response.send_modal(TicketModal(motif=motif))

class TicketModal(discord.ui.Modal):
    def __init__(self, motif: str):
        super().__init__(title=f"Ticket : {motif}")
        self.motif = motif

    precision = discord.ui.TextInput(
        label="Précise ton problème",
        placeholder="Explique brièvement la raison de ton ticket...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        channel_name = f"ticket-{interaction.user.name}".lower()
        ticket_chan = await guild.create_text_channel(name=channel_name, category=category if isinstance(category, discord.CategoryChannel) else None, overwrites=overwrites)

        embed = discord.Embed(
            title=f"🎫 Ticket - {self.motif}",
            description=f"**Demandeur :** {interaction.user.mention}\n**Motif :** {self.motif}\n**Précisions :** {self.precision.value}\n\nUn membre du staff va bientôt te prendre en charge.",
            color=discord.Color.green()
        )
        await ticket_chan.send(content=f"{interaction.user.mention}", embed=embed, view=CloseTicketView())
        
        logs_all = bot.get_channel(LOGS_ALL_ID)
        if logs_all:
            embed_log = discord.Embed(
                title="🎫 Nouveau Ticket Créé",
                description=f"**Demandeur :** {interaction.user.mention}\n**Motif :** {self.motif}\n**Salon :** {ticket_chan.mention}",
                color=discord.Color.green()
            )
            await logs_all.send(embed_log)

        await interaction.followup.send(f"✅ Ton ticket a été créé avec succès : {ticket_chan.mention}", ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.red, custom_id="btn_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fermeture du ticket dans 5 secondes...", ephemeral=True)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass


class DeleteCodeUserView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Traité / Supprimer", style=discord.ButtonStyle.success, custom_id="btn_delete_code_log")
    async def delete_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not est_admin(interaction):
            await interaction.response.send_message("❌ Seul le staff peut valider ceci.", ephemeral=True)
            return
        try:
            await interaction.message.delete()
            await interaction.response.send_message("📦 Log validé et supprimé.", ephemeral=True)
        except Exception:
            pass

class PromoCodeModal(discord.ui.Modal, title="Utiliser un Code Promo"):
    code_input = discord.ui.TextInput(label="Code Promo", placeholder="Entre ton code ici...", required=True, max_length=30)

    async def on_submit(self, interaction: discord.Interaction):
        code = self.code_input.value.strip()
        user_id = interaction.user.id
        user_data = verified_users_data.get(user_id, {"psn": "Non renseigné", "mc": "Non renseigné", "age": "Non renseigné", "surnom": "Non renseigné"})

        logs_codes = bot.get_channel(LOGS_CODES_ID)

        if code not in active_codes:
            if logs_codes:
                embed_rate = discord.Embed(
                    title="❌ Tentative de Code Ratée (Inexistant)",
                    description=(
                        f"**Membre :** {interaction.user.mention} (`{interaction.user}`)\n"
                        f"**Code entré :** `{code}`\n\n"
                        f"📋 **Informations du membre :**\n"
                        f"• **PSN :** {user_data['psn']}\n"
                        f"• **Minecraft :** {user_data['mc']}\n"
                        f"• **Âge :** {user_data['age']}\n"
                        f"• **Surnom :** {user_data['surnom']}"
                    ),
                    color=discord.Color.red()
                )
                await logs_codes.send(embed=embed_rate)
            
            logs_all = bot.get_channel(LOGS_ALL_ID)
            if logs_all:
                await logs_all.send(embed=discord.Embed(title="❌ Code Raté", description=f"{interaction.user.mention} a entré un code invalide : `{code}`", color=discord.Color.red()))

            await interaction.response.send_message("❌ Ce code promo n'existe pas ou est invalide.", ephemeral=True)
            return

        code_data = active_codes[code]
        price = code_data.get("price", 0)
        reward = code_data.get("reward", "Non spécifié")
        reason = code_data.get("reason", "Aucune raison spécifiée")

        if user_id not in user_redeemed_codes:
            user_redeemed_codes[user_id] = []

        already_used = any(
            (item == code if isinstance(item, str) else item.get("code") == code)
            for item in user_redeemed_codes[user_id]
        )
        if already_used:
            if logs_codes:
                embed_already = discord.Embed(
                    title="⚠️ Tentative de Code (Déjà Utilisé)",
                    description=(
                        f"**Membre :** {interaction.user.mention} (`{interaction.user}`)\n"
                        f"**Code entré :** `{code}` (Déjà utilisé)\n\n"
                        f"📋 **Informations du membre :**\n"
                        f"• **PSN :** {user_data['psn']}\n"
                        f"• **Minecraft :** {user_data['mc']}\n"
                        f"• **Âge :** {user_data['age']}\n"
                        f"• **Surnom :** {user_data['surnom']}"
                    ),
                    color=discord.Color.orange()
                )
                await logs_codes.send(embed=embed_already)

            await interaction.response.send_message("❌ Tu as déjà utilisé ce code promo !", ephemeral=True)
            return

        if code_data["uses_left"] <= 0:
            await interaction.response.send_message("❌ Ce code promo a atteint sa limite maximale d'utilisations.", ephemeral=True)
            return

        current_bal = get_money(user_id)
        if current_bal < price:
            await interaction.response.send_message(f"❌ Tu n'as pas assez d'argent ! Ce code coûte **{price} pièces** (tu en as {current_bal}).", ephemeral=True)
            return

        remove_money(user_id, price)
        code_data["uses_left"] -= 1
        
        user_redeemed_codes[user_id].append({
            "code": code,
            "reward": reward,
            "reason": reason
        })
        save_data_main()
        
        if logs_codes:
            embed = discord.Embed(
                title="🎟️ Code Promo Utilisé (Réussi)",
                description=(
                    f"**Membre :** {interaction.user.mention} (`{interaction.user}`)\n"
                    f"**Code :** `{code}`\n"
                    f"**Raison :** {reason}\n"
                    f"**Prix payé :** {price} pièces\n"
                    f"**Récompense :** {reward}\n\n"
                    f"📋 **Informations du membre :**\n"
                    f"• **PSN :** {user_data['psn']}\n"
                    f"• **Minecraft :** {user_data['mc']}\n"
                    f"• **Âge :** {user_data['age']}\n"
                    f"• **Surnom :** {user_data['surnom']}"
                ),
                color=discord.Color.purple()
            )
            embed.set_footer(text=f"ID Utilisateur : {user_id}")
            await logs_codes.send(embed=embed, view=DeleteCodeUserView())

        logs_all = bot.get_channel(LOGS_ALL_ID)
        if logs_all:
            embed_all = discord.Embed(
                title="🎟️ Utilisation d'un Code Promo (Réussi)",
                description=f"**Membre :** {interaction.user.mention}\n**Code :** `{code}`\n**Raison :** {reason}\n**Récompense :** {reward}",
                color=discord.Color.purple()
            )
            await logs_all.send(embed=embed_all)

        await interaction.response.send_message(f"✅ **Code validé !** Tu as payé {price} pièces. Récompense : *{reward}*.", ephemeral=True)

class PromoCodeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Entrer un code", style=discord.ButtonStyle.blurple, custom_id="btn_promo_code")
    async def promo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PromoCodeModal())


class VIPView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="1,00 € - Bronze", url="https://buy.stripe.com/dRm28j7kT6UpeF56wa57W07", style=discord.ButtonStyle.link))
        self.add_item(Button(label="1,50 € - Gold", url="https://buy.stripe.com/aFa4grcFdceJ2WncUy57W08", style=discord.ButtonStyle.link))
        self.add_item(Button(label="2,00 € - Diamond", url="https://buy.stripe.com/14A00b0WvguZ7cD9Im57W09", style=discord.ButtonStyle.link))
        self.add_item(Button(label="2,50 € - Premium", url="https://buy.stripe.com/4gM9ALax5emRaoP8Ei57W0a", style=discord.ButtonStyle.link))
        self.add_item(Button(label="5,00 € - Luxe", url="https://buy.stripe.com/fZu28jax52E9eF55s657W0b", style=discord.ButtonStyle.link))


class BuyItemSelect(discord.ui.Select):
    def __init__(self):
        options = []
        if not active_shop_items:
            options.append(discord.SelectOption(label="Aucun article en boutique", value="none"))
        else:
            for item_name, data in list(active_shop_items.items())[:25]:
                item_type = data.get("type", "Achat")
                stock_str = f" (Stock max: {data['max_stock']})" if data['max_stock'] is not None else ""
                price_str = f" - Prix: {data['price']} pièces"
                options.append(discord.SelectOption(
                    label=f"[{item_type}] {item_name}",
                    description=f"{data['reward'][:30]}{price_str}{stock_str}",
                    value=item_name
                ))
        super().__init__(placeholder="Sélectionne l'article à commander...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Aucun article disponible pour le moment.", ephemeral=True)
            return
        
        item_name = self.values[0]
        item_data = active_shop_items.get(item_name)

        if not item_data:
            await interaction.response.send_message("❌ Cet article n'existe plus.", ephemeral=True)
            return

        if item_data["max_stock"] is not None and item_data["sold"] >= item_data["max_stock"]:
            await interaction.response.send_message("❌ **Rupture de stock !** Cet article a atteint sa limite maximale d'achats.", ephemeral=True)
            return

        user_id = interaction.user.id
        price = item_data.get("price", 0)
        item_type = item_data.get("type", "Achat")

        if item_type.lower() == "achat":
            current_bal = get_money(user_id)
            if current_bal < price:
                await interaction.response.send_message(f"❌ Tu n'as pas assez d'argent ! Cet article coûte **{price} pièces** (tu possèdes {current_bal} pièces).", ephemeral=True)
                return

        await interaction.response.send_modal(BuyItemModal(item_name))

class BuyItemModal(discord.ui.Modal):
    def __init__(self, item_name: str):
        super().__init__(title=f"Commander : {item_name}")
        self.item_name = item_name

    minecraft_pseudo = discord.ui.TextInput(label="Votre pseudo Minecraft exact", placeholder="Ex: MonPseudo...", required=True, max_length=50)
    platform = discord.ui.TextInput(label="Votre plateforme (ex: PS5, PC, etc.)", placeholder="Ex: PS5", required=True, max_length=30)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        item_data = active_shop_items.get(self.item_name)
        if not item_data:
            await interaction.followup.send("❌ Erreur : L'article n'existe plus.", ephemeral=True)
            return

        if item_data["max_stock"] is not None and item_data["sold"] >= item_data["max_stock"]:
            await interaction.followup.send("❌ **Rupture de stock !**", ephemeral=True)
            return

        user_id = interaction.user.id
        price = item_data.get("price", 0)
        item_type = item_data.get("type", "Achat")

        if item_type.lower() == "achat":
            current_bal = get_money(user_id)
            if current_bal < price:
                await interaction.followup.send(f"❌ Solde insuffisant pour finaliser l'achat.", ephemeral=True)
                return
            remove_money(user_id, price)
        else:
            add_money(user_id, price)

        item_data["sold"] += 1
        save_data_main()

        user_data = verified_users_data.get(user_id, {"psn": "Non renseigné", "mc": "Non renseigné", "age": "Non renseigné", "surnom": "Non renseigné"})
        
        embed_logs = discord.Embed(
            title=f"🛒 Commande Boutique [{item_type.upper()}] : {self.item_name}",
            description=(
                f"**Membre :** {interaction.user.mention} (`{interaction.user}`)\n"
                f"**Type :** {item_type}\n"
                f"**Article :** {self.item_name}\n"
                f"**Montant :** {price} pièces\n"
                f"**Détails :** {item_data['reward']}\n"
                f"• **Pseudo Minecraft :** {self.minecraft_pseudo.value}\n"
                f"• **Plateforme :** {self.platform.value}\n\n"
                f"📋 **Informations du membre :**\n"
                f"• **PSN :** {user_data['psn']}\n"
                f"• **Minecraft :** {user_data['mc']}\n"
                f"• **Âge :** {user_data['age']}\n"
                f"• **Surnom :** {user_data['surnom']}"
            ),
            color=discord.Color.green() if item_type.lower() == "achat" else discord.Color.orange()
        )
        embed_logs.set_footer(text=f"ID Utilisateur : {user_id}")

        logs_codes = bot.get_channel(LOGS_CODES_ID)
        if logs_codes:
            await logs_codes.send(embed=embed_logs, view=DeliverOrderView())

        logs_all = bot.get_channel(LOGS_ALL_ID)
        if logs_all:
            await logs_all.send(embed=embed_logs)

        action_text = f"acheté pour {price} pièces" if item_type.lower() == "achat" else f"vendu pour un gain de {price} pièces"
        await interaction.followup.send(f"✅ **Transaction réussie !** Tu a {action_text}. Ta commande de **{self.item_name}** a été transmise au staff.", ephemeral=True)

class ShopBuyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Commander un article", style=discord.ButtonStyle.success, custom_id="btn_shop_buy_main")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not active_shop_items:
            await interaction.response.send_message("❌ Aucun article n'est disponible en boutique pour l'instant.", ephemeral=True)
            return
        
        view = discord.ui.View(timeout=60)
        view.add_item(BuyItemSelect())
        await interaction.response.send_message("📌 **Sélectionne l'article que tu souhaites commander :**", view=view, ephemeral=True)

class DeliverOrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Livré", style=discord.ButtonStyle.success, custom_id="btn_order_delivered")
    async def delivered_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not est_admin(interaction):
            await interaction.response.send_message("❌ Seul le staff peut valider la livraison !", ephemeral=True)
            return

        original_embed = interaction.message.embeds[0] if interaction.message.embeds else None
        
        if original_embed:
            new_embed = discord.Embed(
                title=f"✅ [TRAITÉ] {original_embed.title}",
                description=f"{original_embed.description}\n\n👑 **Traité par :** {interaction.user.mention}",
                color=discord.Color.dark_green()
            )
            for field in original_embed.fields:
                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
            
            await interaction.message.edit(embed=new_embed, view=None)
            
            logs_all = bot.get_channel(LOGS_ALL_ID)
            if logs_all:
                await logs_all.send(embed=new_embed)

            await interaction.response.send_message("📦 Commande marquée comme traitée !", ephemeral=True)
        else:
            await interaction.message.delete()
            await interaction.response.send_message("📦 Commande supprimée avec succès !", ephemeral=True)

# --- SYSTEME DE QUIZ ---
class QuizLevelSelect(discord.ui.Select):
    def __init__(self, niveau: str, start: int = 1, end: int = 25):
        self.niveau = niveau
        options = []
        for i in range(start, end + 1):
            nb_q, argent = get_level_config(i)
            options.append(discord.SelectOption(label=f"Niveau {i}", description=f"Questions: {nb_q} | Gain max: {argent}", value=str(i)))
        super().__init__(placeholder=f"Choisis un niveau ({start} à {end})...", min_values=1, max_values=1, options=options, custom_id=f"quiz_select_{niveau}_{start}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Niveau **{self.values[0]}** sélectionné ({self.niveau.upper()}). Clique sur **Commencer** pour lancer !", ephemeral=True)


class QuizInteractiveView(discord.ui.View):
    def __init__(self, niveau: str, author_id: int, page: int = 1):
        super().__init__(timeout=180)
        self.niveau = niveau
        self.author_id = author_id
        self.page = page
        
        if page == 1:
            self.add_item(QuizLevelSelect(niveau, 1, 25))
        else:
            self.add_item(QuizLevelSelect(niveau, 26, 50))

        self.add_item(QuizPageButton(niveau, author_id, 1, "Tranche 1-25", page == 1))
        self.add_item(QuizPageButton(niveau, author_id, 2, "Tranche 26-50", page == 2))
        self.add_item(QuizStartButton(author_id))


class QuizPageButton(discord.ui.Button):
    def __init__(self, niveau: str, author_id: int, target_page: int, label: str, is_active: bool):
        super().__init__(label=label, style=discord.ButtonStyle.secondary if not is_active else discord.ButtonStyle.primary, custom_id=f"quiz_page_{target_page}_{niveau}", row=1)
        self.niveau = niveau
        self.author_id = author_id
        self.target_page = target_page

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Ce n'est pas ton panneau !", ephemeral=True)
        embed = create_quiz_interactive_embed(self.niveau, self.target_page)
        view = QuizInteractiveView(self.niveau, self.author_id, self.target_page)
        await interaction.response.edit_message(embed=embed, view=view)


class QuizStartButton(discord.ui.Button):
    def __init__(self, author_id: int):
        super().__init__(label="🚀 Commencer", style=discord.ButtonStyle.success, custom_id="quiz_start_game_btn", row=1)
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Ce n'est pas ton menu !", ephemeral=True)

        selected_level = None
        for child in self.view.children:
            if isinstance(child, discord.ui.Select) and child.values:
                selected_level = child.values[0]

        if not selected_level:
            return await interaction.response.send_message("⚠️ Tu dois d'abord choisir un niveau dans le menu déroulant avant de commencer !", ephemeral=True)

        level_num = int(selected_level)
        questions = generate_level_questions(self.view.niveau, level_num)
        view = QuizGameView(questions, interaction.user.id, self.view.niveau, level_num)
        await view.start_quiz(interaction)

def get_level_config(level_num: int):
    nb_questions = (10 + (level_num - 1) * 2) * 2  
    argent = nb_questions  
    return f"{nb_questions} questions", f"{argent} $"

def create_quiz_interactive_embed(niveau: str, page: int = 1):
    title_map = {"facile": "🟢 Tableau des Niveaux - Facile (1 à 50)", "moyens": "🟡 Tableau des Niveaux - Moyens (1 à 50)", "difficile": "🟠 Tableau des Niveaux - Difficile (1 à 50)", "hard": "🔴 Tableau des Niveaux - Hard (1 à 50)"}
    color_map = {"facile": discord.Color.green(), "moyens": discord.Color.gold(), "difficile": discord.Color.orange(), "hard": discord.Color.red()}

    start_idx = 1 if page == 1 else 26
    end_idx = 26 if page == 1 else 51

    table_lines = ["`Niveau` | `Questions` | `Gain Max`", "`------` | `---------` | `--------`"]
    for i in range(start_idx, end_idx):
        nb_q, argent = get_level_config(i)
        table_lines.append(f"Niveau {i:<2} | {nb_q:<11} | {argent}")

    embed = discord.Embed(
        title=title_map.get(niveau, "Tableau des Quiz"),
        description=f"Sélectionne ton niveau dans le menu déroulant, puis clique sur **🚀 Commencer** ➔\n\n```text\n" + "\n".join(table_lines) + "\n```",
        color=color_map.get(niveau, discord.Color.blue())
    )
    embed.set_footer(text=f"Tranche affichée : {start_idx} à {end_idx - 1} sur 50 niveaux (1 pièce par bonne réponse)")
    return embed

def generate_level_questions(niveau: str, level_num: int):
    banque_questions = [
        {"question": "Quel est le résultat de 7 x 8 ?", "choices": ["54", "56", "64", "48"], "answer": 1},
        {"question": "Quelle est la capitale de l'Australie ?", "choices": ["Sydney", "Melbourne", "Canberra", "Perth"], "answer": 2},
        {"question": "Qui a écrit 'Les Misérables' ?", "choices": ["Émile Zola", "Albert Camus", "Victor Hugo", "Molière"], "answer": 2},
        {"question": "En quelle année a débuté la Première Guerre mondiale ?", "choices": ["1914", "1939", "1870", "1918"], "answer": 0},
        {"question": "Quel est le plus grand océan du monde ?", "choices": ["Océan Atlantique", "Océan Indien", "Océan Arctique", "Océan Pacifique"], "answer": 3},
        {"question": "Combien font 15 % de 200 ?", "choices": ["15", "30", "45", "20"], "answer": 1},
        {"question": "Quel gaz compose la majeure partie de l'atmosphère terrestre ?", "choices": ["Oxygène", "Azote", "Dioxyde de carbone", "Hydrogène"], "answer": 1},
        {"question": "Quel est le synonyme du mot 'belliqueux' ?", "choices": ["Amable", "Guerrier", "Pessimiste", "Rapide"], "answer": 1},
        {"question": "Combien de côtés possède un hexagone ?", "choices": ["5", "6", "7", "8"], "answer": 1},
        {"question": "Quel est l'élément chimique dont le symbole est 'O' ?", "choices": ["Or", "Oxygène", "Osmium", "Ozone"], "answer": 1},
        {"question": "Quel traité a mis fin à la Première Guerre mondiale en 1919 ?", "choices": ["Traité de Versailles", "Traité de Paris", "Traité de Westphalie", "Traité de Rome"], "answer": 0},
        {"question": "Quelle est la dérivée de la fonction f(x) = x² ?", "choices": ["2x", "x", "x²", "2"], "answer": 0},
        {"question": "Dans quelle ville se trouve le siège de l'Union Européenne ?", "choices": ["Paris", "Strasbourg", "Bruxelles", "Luxembourg"], "answer": 2},
        {"question": "Quel physicien a formulé la théorie de la relativité restreinte ?", "choices": ["Isaac Newton", "Galilée", "Albert Einstein", "Nikola Tesla"], "answer": 2},
        {"question": "Quelle figure de style utilise l'expression 'pleurer des torrents de larmes' ?", "choices": ["Une métaphore", "Une hyperbole", "Une litote", "Une anaphore"], "answer": 1},
        {"question": "Quel pays possède la plus longue frontière terrestre avec la France ?", "choices": ["L'Espagne", "La Belgique", "L'Italie", "Le Brésil"], "answer": 3},
        {"question": "Quel est le plus grand pays du monde en superficie ?", "choices": ["Canada", "Chine", "États-Unis", "Russie"], "answer": 3},
        {"question": "Quel est le roman célèbre qui commence par 'Longtemps, je me suis couché de bonne heure' ?", "choices": ["À la recherche du temps perdu", "L'Étranger", "Le Petit Prince", "Madame Bovary"], "answer": 0},
        {"question": "En quelle année la chute de Constantinople a-t-elle eu lieu, marquant la fin du Moyen Âge ?", "choices": ["1453", "1492", "1515", "1348"], "answer": 0},
        {"question": "Quel est l'élément chimique dont le symbole est 'W' ?", "choices": ["Le Wolfram (Tungstène)", "Le Brome", "L'Yttrium", "Le Vanadium"], "answer": 0},
        {"question": "Quel auteur a écrit 'À la recherche du temps perdu' ?", "choices": ["Jean-Paul Sartre", "Marcel Proust", "Albert Camus", "Gustave Flaubert"], "answer": 1},
        {"question": "Quelle est la valeur de la constante mathématique 'e' arrondie à deux décimales ?", "choices": ["2.71", "3.14", "1.41", "1.73"], "answer": 0},
        {"question": "Quel roi de France a été surnommé le 'Roi-Soleil' ?", "choices": ["Louis XIV", "Louis XIII", "François Ier", "Henri IV"], "answer": 0},
        {"question": "Quelle est la formule chimique du glucose ?", "choices": ["C6H12O6", "CO2", "H2SO4", "NaCl"], "answer": 0},
        {"question": "Dans quelle mythologie trouve-t-on la divinité Quetzalcoatl ?", "choices": ["Grecque", "Égyptienne", "Aztèque", "Nordique"], "answer": 2}
    ]

    nb_q_str, _ = get_level_config(level_num)
    count = int(nb_q_str.split()[0])
    
    q_list = []
    rng = random.Random(level_num * 99)
    
    for q_idx in range(1, count + 1):
        base_q = rng.choice(banque_questions)
        q_list.append({
            "question": base_q["question"],
            "choices": base_q["choices"],
            "answer": base_q["answer"]
        })
        
    return q_list

class QuizGameView(discord.ui.View):
    def __init__(self, questions, author_id, niveau, level_num, start_index=0):
        super().__init__(timeout=60)
        self.questions = questions
        self.author_id = author_id
        self.niveau = niveau
        self.level_num = level_num
        self.current_question = start_index
        self.score = 0

    async def start_quiz(self, interaction: discord.Interaction):
        await self.send_or_edit(interaction, is_first=True)

    async def update_question(self, interaction: discord.Interaction):
        if self.current_question >= len(self.questions):
            embed = discord.Embed(
                title=f"🏆 Niveau {self.level_num} Terminé [{self.niveau.upper()}]",
                description=f"Bravo ! Tu as terminé le niveau avec **{self.score}/{len(self.questions)}** bonnes réponses.\nTu as gagné **{self.score} pièces** au total (+1 par bonne réponse) 💰",
                color=discord.Color.green()
            )
            for child in self.children:
                child.disabled = True
            
            if interaction.response.is_done():
                await interaction.edit_original_response(content="✅ **Niveau complété !**", embed=embed, view=self)
            else:
                await interaction.response.edit_message(content="✅ **Niveau complété !**", embed=embed, view=self)
            return

        await self.send_or_edit(interaction, is_first=False)

    async def send_or_edit(self, interaction: discord.Interaction, is_first: bool):
        q = self.questions[self.current_question]
        embed = discord.Embed(
            title=f"❓ Quiz [{self.niveau.upper()}] - Niveau {self.level_num} (Question {self.current_question + 1}/{len(self.questions)})",
            description=q["question"],
            color=discord.Color.blue()
        )
        
        self.clear_items()
        for i, choice in enumerate(q["choices"]):
            button = discord.ui.Button(label=choice, style=discord.ButtonStyle.blurple, custom_id=f"q_btn_{i}")
            button.callback = self.create_callback(i, q["answer"])
            self.add_item(button)

        if is_first:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=self, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        else:
            if interaction.response.is_done():
                await interaction.edit_original_response(content=None, embed=embed, view=self)
            else:
                await interaction.response.edit_message(content=None, embed=embed, view=self)

    def create_callback(self, choice_index, correct_index):
        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("❌ Ce n'est pas ton quiz !", ephemeral=True)
                return

            if choice_index == correct_index:
                self.score += 1
                add_money(self.author_id, 1)

            self.current_question += 1
            await self.update_question(interaction)

        return button_callback

# ==========================================
# ÉVÉNEMENTS GLOBAUX
# ==========================================

@bot.event
async def on_ready():
    bot.add_view(ShopView())
    bot.add_view(VerificationView())
    bot.add_view(PromoCodeView())
    bot.add_view(DeliverOrderView())
    bot.add_view(ShopBuyView())
    bot.add_view(DeleteCodeUserView())
    bot.add_view(VIPView())
    
    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchro : {e}")
    print(f"Bot connecté et arborescence synchro en tant que {bot.user} !")

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id")
        
        if custom_id and custom_id.startswith("claim_money_"):
            try:
                amount = int(custom_id.split("_")[2])
                user_id = interaction.user.id
                
                add_money(user_id, amount)
                new_balance = get_money(user_id)
                
                await interaction.response.send_message(
                    f"✅ Succès ! **{amount} pièces** ont été ajoutées à ton solde ! (Nouveau solde : {new_balance} pièces)", 
                    ephemeral=True
                )
                
                await interaction.message.edit(
                    view=None, 
                    content=interaction.message.content + f"\n\n*(Récompense récupérée par {interaction.user.mention} ✅)*"
                )
                
            except Exception as e:
                print(f"Erreur lors de la récupération des pièces : {e}")
                try:
                    await interaction.response.send_message("❌ Une erreur est survenue lors de l'ajout des pièces.", ephemeral=True)
                except:
                    pass

@bot.event
async def on_message_delete(message):
    if message.guild is None or message.author.bot:
        return
    logs_all = bot.get_channel(LOGS_ALL_ID)
    if logs_all:
        embed = discord.Embed(
            title="🗑️ Message Supprimé",
            description=f"**Auteur :** {message.author.mention} (`{message.author}`)\n**Salon :** {message.channel.mention}\n**Contenu :** `{message.content or '[Média / Embed]'}`",
            color=discord.Color.dark_red()
        )
        await logs_all.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.guild is None or before.author.bot or before.content == after.content:
        return
    logs_all = bot.get_channel(LOGS_ALL_ID)
    if logs_all:
        embed = discord.Embed(
            title="✏️ Message Modifié",
            description=f"**Auteur :** {before.author.mention}\n**Salon :** {before.channel.mention}\n**Avant :** `{before.content}`\n**Après :** `{after.content}`",
            color=discord.Color.dark_orange()
        )
        await logs_all.send(embed=embed)

@bot.event
async def on_member_join(member):
    logs_all = bot.get_channel(LOGS_ALL_ID)
    if logs_all:
        embed = discord.Embed(
            title="📥 Nouveau Membre",
            description=f"{member.mention} (`{member}`) a rejoint le serveur.",
            color=discord.Color.green()
        )
        await logs_all.send(embed=embed)

@bot.event
async def on_member_remove(member):
    logs_all = bot.get_channel(LOGS_ALL_ID)
    if logs_all:
        embed = discord.Embed(
            title="📤 Départ d'un Membre",
            description=f"{member.mention} (`{member}`) a quitté le serveur.",
            color=discord.Color.red()
        )
        await logs_all.send(embed=embed)

@bot.event
async def on_message(message):
    # --- INTERCEPTION DU SPYDER BOT / SYNCHRONISATION ARGENT ---
    if "vient de synchroniser" in message.content and "ARKBERN PHONE" in message.content:
        clean_content = message.content.replace("*", "")
        match = re.search(r"(.+?)\s+vient de synchroniser\s+(\d+)\s+pièces\s+depuis\s+ARKBERN\s+PHONE", clean_content, re.IGNORECASE)
        
        if match:
            raw_pseudo = match.group(1).strip()
            raw_pseudo = re.sub(r'^[^\w\s]+', '', raw_pseudo).strip()
            pieces = int(match.group(2).strip())
            
            target_member = None
            if message.guild:
                target_member = discord.utils.get(message.guild.members, name=raw_pseudo)
                if not target_member:
                    target_member = discord.utils.find(lambda m: m.name.lower() == raw_pseudo.lower() or (m.display_name and m.display_name.lower() == raw_pseudo.lower()), message.guild.members)

            if target_member:
                add_money(target_member.id, pieces)
                new_balance = get_money(target_member.id)

                target_channel = bot.get_channel(MONEY_LOG_CHANNEL_ID)
                if target_channel:
                    confirmation_msg = f"✅ Pièces ajoutées ! **{target_member.mention}** vient de recevoir **{pieces} pièces** (Nouveau solde : {new_balance} pièces)."
                    await target_channel.send(confirmation_msg)

    if message.author.bot:
        await bot.process_commands(message)
        return

    content_lower = message.content.lower()
    if any(word in content_lower for word in BAD_WORDS):
        try:
            await message.delete()
        except Exception:
            pass
        
        user_id = message.author.id
        if user_id not in user_warns:
            user_warns[user_id] = 0
        user_warns[user_id] += 1
        save_data_main()

        logs_sanction = bot.get_channel(LOGS_SANCTION_ID)
        if logs_sanction:
            embed = discord.Embed(
                title="⚠️ Message Supprimé (Gros mot)",
                description=f"**Auteur :** {message.author.mention}\n**Salon :** {message.channel.mention}\n**Message :** `{message.content}`",
                color=discord.Color.orange()
            )
            await logs_sanction.send(embed=embed)

        logs_all = bot.get_channel(LOGS_ALL_ID)
        if logs_all:
            embed_all = discord.Embed(
                title="⚠️ Sanction / Message Supprimé",
                description=f"**Auteur :** {message.author.mention}\n**Salon :** {message.channel.mention}",
                color=discord.Color.orange()
            )
            await logs_all.send(embed=embed_all)

        try:
            await message.author.send(f"⚠️ Attention {message.author.mention}, ton message a été supprimé car il contenait un terme interdit sur le serveur.")
        except Exception:
            pass

    await bot.process_commands(message)

# ==========================================
# COMMANDES SLASH : BOUTIQUE JOUEUR
# ==========================================

@bot.tree.command(name="demande_create_sell", description="Proposer un objet à vendre en tant que joueur")
@discord.app_commands.choices(type_prix=[
    discord.app_commands.Choice(name="Pour l'unité", value="Unité"),
    discord.app_commands.Choice(name="Pour le total", value="Total")
])
async def demande_create_sell(interaction: discord.Interaction, objet: str, nombre: int, prix: str, type_prix: str):
    embed = discord.Embed(title="📩 Nouvelle demande de vente d'un joueur", color=discord.Color.orange())
    embed.add_field(name="Membre", value=interaction.user.mention, inline=False)
    embed.add_field(name="Objet", value=objet, inline=True)
    embed.add_field(name="Quantité", value=str(nombre), inline=True)
    embed.add_field(name="Prix", value=f"{prix} ({type_prix})", inline=True)
    
    data = {
        "joueur": interaction.user.name,
        "objet": objet,
        "nombre": nombre,
        "prix": prix,
        "type_prix": type_prix
    }
    
    view = AdminTicketView(data)
    salon_log = interaction.guild.get_channel(LOGS_ALL_ID)
    if salon_log:
        await salon_log.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Ta demande a bien été envoyée aux administrateurs !", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Salon introuvable pour envoyer la demande.", ephemeral=True)

@bot.tree.command(name="objet_delete_shop", description="Supprimer directement l'un de vos objets en vente")
async def objet_delete_shop(interaction: discord.Interaction):
    user_sales_with_index = [(i, v) for i, v in enumerate(VENTES_JOUEURS) if v['joueur'].lower() == interaction.user.name.lower()]
    
    if not user_sales_with_index:
        return await interaction.response.send_message("❌ Tu n'as aucun objet en vente actuellement.", ephemeral=True)

    view = SelectDeleteDirectView(user_sales_with_index)
    await interaction.response.send_message("🗑️ Choisis dans la liste ci-dessous l'objet à supprimer immédiatement :", view=view, ephemeral=True)


# --- COMMANDES ADMIN ---

@bot.tree.command(name="delete_membre_objet_sell", description="[Admin] Supprimer l'objet en vente d'un membre")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def delete_membre_objet_sell(interaction: discord.Interaction, joueur: str, objet: str):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    
    global VENTES_JOUEURS
    avant_len = len(VENTES_JOUEURS)
    VENTES_JOUEURS = [v for v in VENTES_JOUEURS if not (v['joueur'].lower() == joueur.lower() and v['objet'].lower() == objet.lower())]
    
    if len(VENTES_JOUEURS) < avant_len:
        sauvegarder_donnees_boutique()
        await interaction.response.send_message(f"✅ L'objet **{objet}** du joueur **{joueur}** a été supprimé des ventes avec succès !", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Aucun objet **{objet}** trouvé pour le joueur **{joueur}**.", ephemeral=True)

@bot.tree.command(name="create_objetsell", description="[Admin] Créer un objet sell officiel")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def create_objetsell(interaction: discord.Interaction, objet: str, prix: str, stock: int):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    
    OBJETS_SELL.append({"objet": objet, "prix": prix, "stock": stock})
    sauvegarder_donnees_boutique()
    await interaction.response.send_message(f"✅ L'objet **{objet}** a été ajouté avec un stock de **{stock}**.", ephemeral=True)

@bot.tree.command(name="delete_objetsell", description="[Admin] Supprimer un objet sell officiel")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def delete_objetsell(interaction: discord.Interaction, objet: str):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    
    global OBJETS_SELL
    OBJETS_SELL = [o for o in OBJETS_SELL if o['objet'].lower() != objet.lower()]
    sauvegarder_donnees_boutique()
    await interaction.response.send_message(f"✅ Objet officiel **{objet}** supprimé de la liste.", ephemeral=True)

@bot.tree.command(name="sell_objet_player", description="[Admin] Ajouter manuellement une vente joueur au tableau")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
@app_commands.choices(type_prix=[
    discord.app_commands.Choice(name="Pour l'unité", value="Unité"),
    discord.app_commands.Choice(name="Pour le total", value="Total")
])
async def sell_objet_player(interaction: discord.Interaction, joueur: str, objet: str, nombre: int, prix: str, type_prix: str):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    
    data = {"joueur": joueur, "objet": objet, "nombre": nombre, "prix": prix, "type_prix": type_prix}
    VENTES_JOUEURS.append(data)
    sauvegarder_donnees_boutique()
    
    await get_or_create_vendeur_salon(interaction.guild, joueur)
    
    salon = interaction.guild.get_channel(LOGS_ALL_ID)
    if salon:
        embed = discord.Embed(title="🛒 Vente joueur ajoutée manuellement", color=discord.Color.blue())
        embed.add_field(name="Joueur", value=joueur, inline=True)
        embed.add_field(name="Objet", value=objet, inline=True)
        embed.add_field(name="Quantité", value=str(nombre), inline=True)
        embed.add_field(name="Prix", value=f"{prix} ({type_prix})", inline=True)
        await salon.send(embed=embed)
        
    await interaction.response.send_message("✅ Vente ajoutée au tableau avec succès !", ephemeral=True)

@bot.tree.command(name="pannel_boutique", description="[Admin] Afficher le panneau récapitulatif de la boutique")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def pannel_boutique(interaction: discord.Interaction):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    
    embed = discord.Embed(title="📊 Tableau de la Boutique / Ventes", color=discord.Color.gold())
    
    off_lines = "```text\n"
    off_lines += f"{'Vendeur':<15} | {'Item':<10} | {'Stock':<8} | {'Prix':<8}\n"
    off_lines += "-" * 48 + "\n"
    if OBJETS_SELL:
        for o in OBJETS_SELL:
            off_lines += f"{'Officiel':<15} | {o['objet']:<10} | {str(o['stock']):<8} | {str(o['prix']):<8}\n"
    else:
        off_lines += "Aucun objet officiel disponible.\n"
    off_lines += "```"
    embed.add_field(name="📦 Objets Sell Officiels", value=off_lines, inline=False)
    
    joueur_lines = "```text\n"
    joueur_lines += f"{'Vendeur':<15} | {'Item':<10} | {'Quantité':<8} | {'Prix':<8}\n"
    joueur_lines += "-" * 48 + "\n"
    if VENTES_JOUEURS:
        for v in VENTES_JOUEURS:
            p_display = f"{v['prix']} ({v.get('type_prix', 'Total')})"
            joueur_lines += f"{v['joueur']:<15} | {v['objet']:<10} | {str(v['nombre']):<8} | {p_display:<8}\n"
    else:
        joueur_lines += "Aucune vente de joueur active.\n"
    joueur_lines += "```"
    embed.add_field(name="👥 Ventes des Joueurs", value=joueur_lines, inline=False)
    
    view = BoutiqueTableView()
    await interaction.response.send_message(embed=embed, view=view)


# ==========================================
# COMMANDES SLASH : SYSTEME PRINCIPAL
# ==========================================

@bot.tree.command(name="messages", description="Ouvre l'application de messagerie interne entre membres vérifiés")
async def messages_app(interaction: discord.Interaction):
    if interaction.user.id not in verified_users_data:
        await interaction.response.send_message("❌ Tu d'abord valider ta vérification sur le serveur pour utiliser l'application de messages !", ephemeral=True)
        return
    embed = discord.Embed(title="📱 ARKBERN MESSAGE - APPLICATION", description="Bienvenue dans ta messagerie interne sécurisée.\nChoisis une option ci-dessous pour envoyer ou consulter tes messages :", color=discord.Color.blurple())
    embed.set_footer(text="Réservé aux membres vérifiés")
    view = MessageAppView(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="balance", description="Affiche ton solde d'argent")
async def balance(interaction: discord.Interaction):
    target = interaction.user
    bal = get_money(target.id)
    embed = discord.Embed(title="💰 Ton Portefeuille", description=f"Tu possèdes actuellement **{bal} pièces**.", color=discord.Color.gold())
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="envoyer_argent", description="Envoie un bouton pour distribuer de l'argent dans un salon (Admin)")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
@app_commands.describe(montant="Le montant de pièces à distribuer")
async def envoyer_argent(interaction: discord.Interaction, montant: int):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    target_channel_id = MONEY_LOG_CHANNEL_ID
    channel = bot.get_channel(target_channel_id)
    if not channel:
        return await interaction.response.send_message("❌ Impossible de trouver le salon spécifié avec cet ID.", ephemeral=True)

    embed = discord.Embed(title="🎁 Distribution d'Argent !", description=f"Clique sur le bouton ci-dessous pour récupérer **{montant} pièces** !", color=discord.Color.gold())
    view = discord.ui.View(timeout=None)
    button = discord.ui.Button(label=f"Récupérer {montant} pièces", style=discord.ButtonStyle.success, custom_id=f"claim_money_{montant}", emoji="💰")
    view.add_item(button)

    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Le message de distribution a été envoyé directement dans <#{target_channel_id}> !", ephemeral=True)

@bot.tree.command(name="add", description="Ajoute de l'argent à un membre (Admin)")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def add_money_cmd(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    if montant <= 0:
        return await interaction.response.send_message("❌ Le montant doit être supérieur à 0.", ephemeral=True)
    add_money(membre.id, montant)
    new_bal = get_money(membre.id)
    logs_all = bot.get_channel(LOGS_ALL_ID)
    if logs_all:
        await logs_all.send(embed=discord.Embed(title="💰 Ajout d'Argent", description=f"**Admin :** {interaction.user.mention}\n**Membre :** {membre.mention}\n**Montant :** +{montant} pièces\n**Nouveau solde :** {new_bal} pièces", color=discord.Color.gold()))
    await interaction.response.send_message(f"✅ Ajout de **{montant} pièces** à {membre.mention}. Nouveau solde : {new_bal} pièces.", ephemeral=True)

@bot.tree.command(name="delete", description="Retire de l'argent à un membre (Admin)")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def delete_money_cmd(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    if montant <= 0:
        return await interaction.response.send_message("❌ Le montant doit être supérieur à 0.", ephemeral=True)
    remove_money(membre.id, montant)
    new_bal = get_money(membre.id)
    logs_all = bot.get_channel(LOGS_ALL_ID)
    if logs_all:
        await logs_all.send(embed=discord.Embed(title="💸 Retrait d'Argent", description=f"**Admin :** {interaction.user.mention}\n**Membre :** {membre.mention}\n**Montant :** -{montant} pièces\n**Nouveau solde :** {new_bal} pièces", color=discord.Color.red()))
    await interaction.response.send_message(f"✅ Retrait de **{montant} pièces** à {membre.mention}. Nouveau solde : {new_bal} pièces.", ephemeral=True)

@bot.tree.command(name="create_ticket", description="Crée un ticket manuellement pour un joueur avec une raison (Admin)")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def create_ticket(interaction: discord.Interaction, joueur: discord.Member, raison: str):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        joueur: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    channel_name = f"ticket-{joueur.name}".lower()
    ticket_chan = await guild.create_text_channel(name=channel_name, category=category if isinstance(category, discord.CategoryChannel) else None, overwrites=overwrites)
    embed = discord.Embed(title=f"🎫 Ticket Admin - {raison}", description=f"**Demandeur / Concerné :** {joueur.mention}\n**Créé par :** {interaction.user.mention}\n**Raison :** {raison}\n\nUn staff va s'occuper de ce ticket.", color=discord.Color.green())
    await ticket_chan.send(content=f"{joueur.mention} {interaction.user.mention}", embed=embed, view=CloseTicketView())
    await interaction.followup.send(f"✅ Le ticket pour {joueur.mention} a été créé avec succès : {ticket_chan.mention}", ephemeral=True)

@bot.tree.command(name="quiz_facile", description="Affiche le tableau (Facile)")
async def quiz_facile(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_quiz_interactive_embed("facile", 1), view=QuizInteractiveView("facile", interaction.user.id, 1), ephemeral=True)

@bot.tree.command(name="quiz_moyens", description="Affiche le tableau (Moyens)")
async def quiz_moyens(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_quiz_interactive_embed("moyens", 1), view=QuizInteractiveView("moyens", interaction.user.id, 1), ephemeral=True)

@bot.tree.command(name="quiz_difficile", description="Affiche le tableau (Difficile)")
async def quiz_difficile(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_quiz_interactive_embed("difficile", 1), view=QuizInteractiveView("difficile", interaction.user.id, 1), ephemeral=True)

@bot.tree.command(name="quiz_hard", description="Affiche le tableau (Hard)")
async def quiz_hard(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_quiz_interactive_embed("hard", 1), view=QuizInteractiveView("hard", interaction.user.id, 1), ephemeral=True)

@bot.tree.command(name="shop", description="Affiche le catalogue de tous les articles disponibles (Achats & Ventes)")
async def shop_catalogue(interaction: discord.Interaction):
    embed = get_shop_embed()
    if interaction.response.is_done():
        await interaction.message.edit(embed=embed, view=ShopBuyView())
    else:
        await interaction.response.send_message(embed=embed, view=ShopBuyView(), ephemeral=True)

@bot.tree.command(name="create_objetshop", description="Crée un article dans la boutique (Achat ou Vente)")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
@app_commands.choices(type_action=[app_commands.Choice(name="Achat", value="Achat"), app_commands.Choice(name="Vente", value="Vente")])
async def create_objetshop(interaction: discord.Interaction, type_action: app_commands.Choice[str], nom: str, recompense: str, prix: int, max_stock: int = None):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    
    active_shop_items[nom] = {
        "type": type_action.value,
        "reward": recompense,
        "price": prix,
        "max_stock": max_stock,
        "sold": 0
    }
    save_data_main()
    await interaction.response.send_message(f"✅ L'article **{nom}** ({type_action.value}) a été ajouté à la boutique avec succès !", ephemeral=True)

@bot.tree.command(name="delete_objetshop", description="[Admin] Supprimer un article de la boutique")
@app_commands.checks.has_any_role(ADMIN_ROLE_ID)
async def delete_objetshop(interaction: discord.Interaction, nom: str):
    if not est_admin(interaction):
        return await interaction.response.send_message("❌ Réservé à l'administrateur.", ephemeral=True)
    
    if nom in active_shop_items:
        del active_shop_items[nom]
        save_data_main()
        await interaction.response.send_message(f"✅ L'article **{nom}** a été supprimé de la boutique.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Aucun article nommé **{nom}** n'a été trouvé.", ephemeral=True)

# Lancement du bot
token = charger_token()
if token:
    bot.run(token)
else:
    print("❌ Erreur : Aucun token valide trouvé dans config.json !")