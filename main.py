import discord
from discord.ext import commands
from gtts import gTTS
import os
from dotenv import load_dotenv
import asyncio
import random
import datetime
import shutil
import subprocess

load_dotenv()

# Installe FFmpeg au démarrage
async def setup_ffmpeg():
    if not shutil.which("ffmpeg"):
        try:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "ffmpeg"], check=True)
        except:
            pass

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix=";", intents=intents)
bot.remove_command("help")

# ==================== SALONS CONFIGURÉS ====================
SALON_LOGS_ROLES_ID = 1535831171726971061    # Logs rôles
SALON_BIENVENUE_ID = 1546103059925438464     # Message bienvenue + mise à jour auto
# ============================================================

messages_bienvenue = {}

@bot.event
async def on_ready():
    await setup_ffmpeg()
    print(f"{bot.user} est connecté !")

# ==================================================
# ✅ LOGS DE RÔLES — VERSION SANS DOUBLON
# ==================================================
@bot.event
async def on_member_update(ancien_membre, nouveau_membre):
    if ancien_membre.bot or nouveau_membre.bot:
        return

    salon_logs = bot.get_channel(SALON_LOGS_ROLES_ID)
    if not salon_logs:
        return

    anciens_roles = set(ancien_membre.roles)
    nouveaux_roles = set(nouveau_membre.roles)

    role_retire = list(anciens_roles - nouveaux_roles)
    role_ajoute = list(nouveaux_roles - anciens_roles)

    # Retire @everyone de la liste
    role_retire = [r for r in role_retire if r.name != "@everyone"]
    role_ajoute = [r for r in role_ajoute if r.name != "@everyone"]

    # === RÔLES RETIRÉS — UN SEUL MESSAGE ===
    if role_retire:
        roles_texte = "\n".join(f"• {r.mention}" for r in role_retire)

        auteur = "❓ Impossible à déterminer"
        try:
            async for entree in ancien_membre.guild.audit_logs(limit=10, action=discord.AuditLogAction.member_role_update):
                if entree.target == nouveau_membre:
                    auteur = entree.user.mention
                    break
        except Exception as e:
            print(f"Erreur logs : {e}")

        embed = discord.Embed(title="❌ RÔLE(S) RETIRÉ(S)", color=discord.Color.red())
        embed.add_field(name="Membre concerné", value=f"{nouveau_membre.mention}", inline=False)
        embed.add_field(name="Rôle(s) retiré(s)", value=roles_texte, inline=False)
        embed.add_field(name="Par", value=auteur, inline=False)
        embed.set_thumbnail(url=nouveau_membre.display_avatar.url)
        await salon_logs.send(embed=embed)

    # === RÔLES AJOUTÉS — UN SEUL MESSAGE ===
    if role_ajoute:
        roles_texte = "\n".join(f"• {r.mention}" for r in role_ajoute)

        auteur = "❓ Impossible à déterminer"
        try:
            async for entree in nouveau_membre.guild.audit_logs(limit=10, action=discord.AuditLogAction.member_role_update):
                if entree.target == nouveau_membre:
                    auteur = entree.user.mention
                    break
        except Exception as e:
            print(f"Erreur logs : {e}")

        embed = discord.Embed(title="✅ RÔLE(S) AJOUTÉ(S)", color=discord.Color.green())
        embed.add_field(name="Membre concerné", value=f"{nouveau_membre.mention}", inline=False)
        embed.add_field(name="Rôle(s) ajouté(s)", value=roles_texte, inline=False)
        embed.add_field(name="Par", value=auteur, inline=False)
        embed.set_thumbnail(url=nouveau_membre.display_avatar.url)
        await salon_logs.send(embed=embed)

    # === MISE À JOUR AUTO DU MESSAGE DE BIENVENUE ===
    if nouveau_membre.id not in messages_bienvenue:
        return

    salon_bienvenue = bot.get_channel(SALON_BIENVENUE_ID)
    if not salon_bienvenue:
        return

    try:
        message = await salon_bienvenue.fetch_message(messages_bienvenue[nouveau_membre.id])
    except:
        return

    if anciens_roles == nouveaux_roles:
        return

    nb_roles = len(nouveau_membre.roles) - 1
    role_plus_haut = nouveau_membre.top_role.name if nb_roles > 0 else "Aucun rôle"
    pseudo_perso = f"Oui : {nouveau_membre.nick}" if nouveau_membre.nick else "Non"
    couleur_rang = str(nouveau_membre.color).upper() if str(nouveau_membre.color) != "#000000" else "Défaut"
    couleur_embed = nouveau_membre.color if str(nouveau_membre.color) != "#000000" else discord.Color.blue()
    est_bot = "Bot" if nouveau_membre.bot else "Membre réel"
    date_creation = nouveau_membre.created_at.strftime("%d/%m/%Y à %H:%M:%S")
    maintenant = datetime.datetime.now(datetime.timezone.utc)
    age_compte = maintenant - nouveau_membre.created_at
    jours = age_compte.days
    annees = jours // 365
    mois_restants = (jours % 365) // 30
    jours_restants = jours % 30

    if jours < 7:
        anciennete = f"Compte neuf — {jours} jours"
    elif jours < 30:
        anciennete = f"Compte récent — {jours} jours"
    elif jours < 180:
        anciennete = f"Compte jeune — {mois_restants} mois {jours_restants} j"
    elif jours < 365:
        anciennete = f"Compte fiable — {mois_restants} mois {jours_restants} j"
    else:
        anciennete = f"Compte ancien — {annees} ans {mois_restants} mois"

    desc = f"""**Membre :** {nouveau_membre.mention}
**Pseudo :** {nouveau_membre.name}
**Surnom :** {pseudo_perso}
**ID :** `{nouveau_membre.id}`
**Type :** {est_bot}
**Créé le :** {date_creation}
**Ancienneté :** {anciennete}
**Nb rôles :** {nb_roles}
**Rang :** {role_plus_haut}
**Couleur :** `{couleur_rang}`"""

    embed = discord.Embed(title="🎉 NOUVEAU MEMBRE ARRIVÉ", description=desc, color=couleur_embed)
    embed.set_thumbnail(url=nouveau_membre.display_avatar.url)
    embed.set_footer(text=f"ID : {nouveau_membre.id} | Mise à jour auto")
    await message.edit(embed=embed)
    print(f"🔄 MAJ : {nouveau_membre.name}")

# ==================================================
# ✅ MESSAGE BIENVENUE À L'ARRIVÉE + MISE À JOUR
# ==================================================
@bot.event
async def on_member_join(membre):
    salon = bot.get_channel(SALON_BIENVENUE_ID)
    if not salon:
        return

    maintenant = datetime.datetime.now(datetime.timezone.utc)
    date_rejoint = maintenant.strftime("%d/%m/%Y à %H:%M:%S")
    date_creation = membre.created_at.strftime("%d/%m/%Y à %H:%M:%S")
    age_compte = maintenant - membre.created_at
    jours = age_compte.days
    annees = jours // 365
    mois_restants = (jours % 365) // 30
    jours_restants = jours % 30

    if jours < 7:
        anciennete = f"Compte neuf — {jours} jours"
    elif jours < 30:
        anciennete = f"Compte récent — {jours} jours"
    elif jours < 180:
        anciennete = f"Compte jeune — {mois_restants} mois {jours_restants} j"
    elif jours < 365:
        anciennete = f"Compte fiable — {mois_restants} mois {jours_restants} j"
    else:
        anciennete = f"Compte ancien — {annees} ans {mois_restants} mois"

    est_bot = "Bot" if membre.bot else "Membre réel"
    nb_roles = len(membre.roles) - 1
    role_plus_haut = membre.top_role.name if nb_roles > 0 else "Aucun rôle"
    pseudo_perso = f"Oui : {membre.nick}" if membre.nick else "Non"
    couleur_rang = str(membre.color).upper() if str(membre.color) != "#000000" else "Défaut"
    couleur_embed = membre.color if str(membre.color) != "#000000" else discord.Color.blue()

    desc = f"""**Membre :** {membre.mention}
**Pseudo :** {membre.name}
**Surnom :** {pseudo_perso}
**ID :** `{membre.id}`
**Type :** {est_bot}
**Créé le :** {date_creation}
**A rejoint le :** {date_rejoint}
**Ancienneté :** {anciennete}
**Nb rôles :** {nb_roles}
**Rang :** {role_plus_haut}
**Couleur :** `{couleur_rang}`"""

    embed_bienvenue = discord.Embed(title="🎉 NOUVEAU MEMBRE ARRIVÉ", description=desc, color=couleur_embed)
    embed_bienvenue.set_thumbnail(url=membre.display_avatar.url)
    embed_bienvenue.set_footer(text=f"ID : {membre.id} | Mise à jour auto")
    message_envoye = await salon.send(embed=embed_bienvenue)
    messages_bienvenue[membre.id] = message_envoye.id
    print(f"✅ Bienvenue : {membre.name}")

# ==================================================
# 🛠️ TES COMMANDES
# ==================================================
@bot.command(name="join")
async def rejoindre(ctx):
    await ctx.message.delete()
    if ctx.author.voice and ctx.author.voice.channel:
        canal = ctx.author.voice.channel
        await canal.connect()
        await ctx.send(f"✅ J'ai rejoint {canal.name}")
    else:
        await ctx.send("❌ Tu dois être dans un canal vocal d'abord !")

@bot.command(name="leave")
async def quitter(ctx):
    await ctx.message.delete()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Je quitte le canal vocal")
    else:
        await ctx.send("❌ Je ne suis pas dans un canal vocal")

@bot.command(name="say")
async def dire(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name="clear")
async def effacer(ctx, nombre: int = 5):
    await ctx.message.delete()
    if nombre < 1:
        nombre = 1
    elif nombre > 100:
        nombre = 100
    messages_supprimes = await ctx.channel.purge(limit=nombre + 1)
    confirmation = await ctx.send(f"🧹 {len(messages_supprimes) - 1} messages supprimés !")
    await asyncio.sleep(3)
    await confirmation.delete()

@bot.command(name="tts")
async def dire_voix(ctx, *, texte: str):
    await ctx.message.delete()
    if not ctx.voice_client:
        return await ctx.send("❌ Utilise d'abord ;join")
    if os.path.exists("message_tts.mp3"):
        os.remove("message_tts.mp3")
    tts = gTTS(text=texte, lang="fr")
    tts.save("message_tts.mp3")
    ctx.voice_client.play(
        discord.FFmpegPCMAudio("message_tts.mp3"),
        after=lambda e: print("TTS terminé" if not e else f"Erreur: {e}")
    )
    await ctx.send(f"🗣️ Je dis : {texte}")

@bot.command(name="pileouface")
async def pile_ou_face(ctx):
    await ctx.message.delete()
    resultat = random.choice(["🪙 **PILE** !", "🪙 **FACE** !"])
    embed = discord.Embed(title="🪙 Pile ou Face", description=f"Résultat : {resultat}", color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(name="sondage")
async def creer_sondage(ctx, question, choix1, choix2):
    await ctx.message.delete()
    embed = discord.Embed(title="📊 SONDAGE", description=f"**{question}**", color=discord.Color.purple())
    embed.add_field(name="🔵 Option 1", value=choix1, inline=False)
    embed.add_field(name="🔴 Option 2", value=choix2, inline=False)
    embed.set_footer(text=f"Sondage de {ctx.author.display_name}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🔵")
    await msg.add_reaction("🔴")

@bot.command(name="blague")
async def raconter_blague(ctx):
    await ctx.message.delete()
    blagues = [
        "Pourquoi les plongeurs plongent toujours en arrière et jamais en avant ?\n➡️ Parce que sinon ils tombent dans le bateau ! 😂",
        "Quel est le fromage préféré des fantômes ?\n➡️ Le Boursoufff ! 👻",
        "Que dit un feu quand il court ?\n➡️ Je suis en feu ! 🔥",
        "Pourquoi les poules n'ont pas de bras ?\n➡️ Parce qu'elles auraient trop l'air con à se faire la bise ! 🐔",
        "Quel est l'arbre le plus facile à tirer au sort ?\n➡️ Le sapin, parce qu'il n'a pas de puces ! 🌲",
        "Deux escargots se rencontrent. L'un dit :\n➡️ Tu as l'air fatigué, toi ! 🐌"
    ]
    blague_choisie = random.choice(blagues)
    embed = discord.Embed(title="😂 Une blague !", description=blague_choisie, color=discord.Color.yellow())
    await ctx.send(embed=embed)

@bot.command(name="help")
async def aide(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="📋 Commandes du Bot", color=discord.Color.blue())
    embed.add_field(name="🎧 Vocales", value="`;join` → Rejoindre\n`;leave` → Quitter", inline=False)
    embed.add_field(name="💬 Texte", value="`;say msg` → Répéter\n`;clear [nb]` → Supprimer", inline=False)
    embed.add_field(name="🎮 Fun", value="`;pileouface` → Pile ou Face\n`;sondage Q A B` → Sondage\n`;blague` → Blague", inline=False)
    embed.add_field(name="ℹ️ Autres", value="`;help` → Cette liste", inline=False)
    embed.set_footer(text=f"Demandé par {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.event
async def on_command(ctx):
    print(f"📝 {ctx.author} → {ctx.command.name}")

TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
