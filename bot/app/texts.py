from __future__ import annotations

from app.settings import settings

DEFAULT_WELCOME = (
    "<b>━━━━━━━━━━━━━━━━━━━━━\n"
    "⚡️ ᴛʜᴇᴅʀᴜɴᴋʙᴏᴛs ⚡️\n"
    "━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    "<blockquote>ᴡᴇʟᴄᴏᴍᴇ, {mention}!\n\n"
    "ɪ ᴀᴍ ᴀ <b>ᴍᴜʟᴛɪ-ᴜsᴇʀ ғɪʟᴇ ᴅᴏᴡɴʟᴏᴀᴅᴇʀ</b> ꜰᴏʀ "
    "ꜰʟᴇᴢᴇɴ, ᴅɪsᴋᴡᴀʟᴀ, ᴠɪᴅʙᴜɴᴋᴇʀ, ᴛᴇʀᴀʙᴏx ᴀɴᴅ ᴜᴘꜰɪʟᴇs.\n\n"
    "◈ sᴛʀᴇᴀᴍ ᴏʀ ᴏᴘᴇɴ ᴅɪʀᴇᴄᴛ ʟɪɴᴋs\n"
    "◈ sᴇɴᴅ ꜰɪʟᴇs ᴛᴏ ᴛʜɪs ᴄʜᴀᴛ\n"
    "◈ ᴜsᴇ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs ꜰᴏʀ ʜɪɢʜᴇʀ ʟɪᴍɪᴛs\n"
    "◈ ᴘʀᴏᴛᴇᴄᴛᴇᴅ ꜰɪʟᴇs ᴡɪᴛʜ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ</blockquote>\n\n"
    "sᴇɴᴅ ᴀ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ."
)

HELP = (
    "<b>━━━━━━━━━━━━━━━━━━━━━\n"
    "📖 ʜᴇʟᴘ & ɢᴜɪᴅᴇ\n"
    "━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    "<blockquote>❶ sᴇɴᴅ ᴀ ᴘᴜʙʟɪᴄ ʟɪɴᴋ ꜰʀᴏᴍ ᴀ sᴜᴘᴘᴏʀᴛᴇᴅ sᴇʀᴠɪᴄᴇ.\n"
    "❷ ᴘɪᴄᴋ sᴛʀᴇᴀᴍ, ᴅɪʀᴇᴄᴛ ᴅᴏᴡɴʟᴏᴀᴅ ᴏʀ sᴇɴᴅ ꜰɪʟᴇ.\n"
    "❸ ᴜᴘʟᴏᴀᴅᴇᴅ ғɪʟᴇs ᴀʀᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇᴅ ᴀꜰᴛᴇʀ {minutes} ᴍɪɴᴜᴛᴇs.</blockquote>\n\n"
    "<b>ᴜsᴇʀ ᴄᴏᴍᴍᴀɴᴅs</b>\n"
    "<code>/start</code> — ᴏᴘᴇɴ ᴛʜᴇ ʙᴏᴛ\n"
    "<code>/help</code> — sʜᴏᴡ ᴛʜɪs ɢᴜɪᴅᴇ\n"
    "<code>/premium</code> — ᴠɪᴇᴡ ᴘʟᴀɴs\n"
    "<code>/myplan</code> — ᴠɪᴇᴡ ʏᴏᴜʀ ʟɪᴍɪᴛs"
).format(minutes=settings.auto_delete_minutes)

OWNER_HELP = (
    "<b>━━━━━━━━━━━━━━━━━━━━━\n"
    "🛠 ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟs\n"
    "━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    "ᴜsᴇ ᴛʜᴇ ᴘᴀɴᴇʟ ʙᴇʟᴏᴡ. ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs ᴀʀᴇ ᴏɴʟʏ ᴠɪsɪʙʟᴇ ᴛᴏ ᴀᴅᴍɪɴs.\n\n"
    "<code>/addpremium r|s|v user_id days</code>\n"
    "<code>/removepremium user_id</code>\n"
    "<code>/add_admin user_id</code> · <code>/remove_admin user_id</code>\n"
    "<code>/addforcesub channel invite_url</code>\n"
    "<code>/removeforcesub channel</code>\n"
    "<code>/setstartphoto</code> · <code>/clearstartphoto</code>\n"
    "<code>/setplan key price days batch total</code> · <code>/deleteplan key</code>"
)

DETECTING = "<b>ᴄʜᴇᴄᴋɪɴɢ ʟɪɴᴋ</b>\n<blockquote>ᴛʜᴇ ʟɪɴᴋ ɪs ɪɴ ᴛʜᴇ ǫᴜᴇᴜᴇ. ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ᴀʀᴇ ᴘʀɪᴏʀɪᴛɪᴢᴇᴅ.</blockquote>"
ANALYSING = "<b>ᴀɴᴀʟʏsɪɴɢ sʜᴀʀᴇ</b>\n<blockquote>ᴅᴏᴍᴀɪɴ: {domain}\nɪᴅ: {surl}</blockquote>"
RETRIEVING = "<b>ғᴇᴛᴄʜɪɴɢ ғɪʟᴇ ᴅᴇᴛᴀɪʟs</b>\n<blockquote>ᴛʜɪs ᴍᴀʏ ᴛᴀᴋᴇ ᴀ ꜰᴇᴡ sᴇᴄᴏɴᴅs.</blockquote>"
RESOLVING = "<b>ᴏᴘᴛɪᴏɴs ʀᴇᴀᴅʏ</b>\n<blockquote>ᴄʜᴏᴏsᴇ ʜᴏᴡ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴜsᴇ ᴛʜɪs ꜰɪʟᴇ.</blockquote>"
READY = "<b>✅ ғɪʟᴇ ʀᴇᴀᴅʏ</b>\n<blockquote>{filename}\n{size} · {kind}</blockquote>\nᴄʜᴏᴏsᴇ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ."
FOLDER = "<b>📁 ғɪʟᴇs ʀᴇᴀᴅʏ</b>\n<blockquote>{title}\n{count} ғɪʟᴇs · {size}</blockquote>\npɪᴄᴋ ᴏɴᴇ ꜰʀᴏᴍ ᴛʜᴇ ʟɪsᴛ."
FINISHED = "<b>✅ ᴅᴏɴᴇ</b>\n<blockquote>{filename}\n{size} · {speed} ᴀᴠᴇʀᴀɢᴇ\nᴄᴏᴍᴘʟᴇᴛᴇᴅ ɪɴ {duration}</blockquote>"
TOO_LARGE = "<b>ғɪʟᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ</b>\n<blockquote>ᴛʜɪs ғɪʟᴇ ɪs {size} ᴀɴᴅ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ sᴇɴᴅ ʟɪᴍɪᴛ ɪs {limit} ᴍʙ.</blockquote>\n\n{hint}"
LARGE_UPLOAD_UNAVAILABLE = "<b>ʟᴀʀɢᴇ ғɪʟᴇ sᴇɴᴅ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ</b>\n<blockquote>sᴛʀᴇᴀᴍ ᴏʀ ᴅɪʀᴇᴄᴛ ᴅᴏᴡɴʟᴏᴀᴅ ᴀʀᴇ sᴛɪʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ.</blockquote>"
NO_LINK = "<b>ɴᴏ sᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋ ғᴏᴜɴᴅ</b>\n\nsᴇɴᴅ ᴀ ᴘᴜʙʟɪᴄ ʟɪɴᴋ ꜰʀᴏᴍ ғʟᴇᴢᴇɴ, ᴅɪsᴋᴡᴀʟᴀ, ᴠɪᴅʙᴜɴᴋᴇʀ, ᴛᴇʀᴀʙᴏx ᴏʀ ᴜᴘꜰɪʟᴇs."
PRIVATE = "<b>ᴘʀɪᴠᴀᴛᴇ ʙᴏᴛ</b>\nᴀsᴋ ᴛʜᴇ ᴏᴡɴᴇʀ ᴛᴏ ᴀᴜᴛʜᴏʀɪsᴇ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ."
BANNED = "<b>⛔ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ</b>\nʏᴏᴜ ᴄᴀɴɴᴏᴛ ᴜsᴇ ᴛʜɪs ʙᴏᴛ."
MAINTENANCE = "<b>🛠 ᴛᴇᴍᴘᴏʀᴀʀʏ ᴘᴀᴜsᴇ</b>\nᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ sʜᴏʀᴛʟʏ."
FAILED = "<b>❌ ᴛʜᴀᴛ ᴅɪᴅɴ’ᴛ ᴡᴏʀᴋ</b>\n<blockquote>{reason}</blockquote>\nᴄʜᴇᴄᴋ ᴛʜᴇ ʟɪɴᴋ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
NOT_OWNER = "<b>ᴀᴅᴍɪɴ ᴏɴʟʏ</b>\nᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ᴛᴏ ʀᴇɢᴜʟᴀʀ ᴜsᴇʀs."

ADMIN_PANEL = (
    "<b>━━━━━━━━━━━━━━━━━━━━━\n"
    "🛠 ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ\n"
    "━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    "<blockquote>ᴜsᴇʀs: {users}\n"
    "ᴅᴏᴡɴʟᴏᴀᴅs: {downloads}\n"
    "ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ: {premium}\n"
    "ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ: {maintenance}\n"
    "ǫᴜᴇᴜᴇᴅ ᴛᴀsᴋs: {queue}</blockquote>\n\n"
    "ᴄʜᴏᴏsᴇ ᴀ sᴇᴄᴛɪᴏɴ ʙᴇʟᴏᴡ."
)


def welcome(mention: str = "there") -> str:
    custom = settings.welcome_text.strip()
    return (custom or DEFAULT_WELCOME).replace("{mention}", mention)