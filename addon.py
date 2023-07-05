import sys
import xbmc

from resources.lib import kodiutil
from resources.lib import main
from resources.lib import settings
from resources.lib import player
from resources.lib import pseutil

if __name__ == '__main__':
    arg = None
    if len(sys.argv) > 1:
        args = sys.argv[1:] or False
        arg = args.pop(0)
        # print '[- PreShow Experience -]: Passed args: {0}'.format(repr(sys.argv))

    if arg == 'trailer.clearWatched':
        settings.clearDBWatchedStatus()
    elif arg == 'trailer.clearBroken':
        settings.clearDBBrokenStatus()
    elif arg == 'experience':
        player.begin(args=args)
    elif str(arg).startswith('dbtype='):
        if args:
            player.begin(dbtype=arg[7:], args=args)
        else:
            xbmc.log('[- PreShow Experience -]: Passed {0} with no dbid)'.format(arg))
    elif str(arg).startswith('movieid='):
        player.begin(movieid=arg[8:], args=args)
    elif str(arg).startswith('episodeid='):
        player.begin(episodeid=arg[10:], args=args)
    elif arg == 'selection':
        player.begin(selection=True, args=args)
    elif arg == 'update.database':
        fromSettings = bool(args and args[0] == 'from.settings')
        pseutil.loadContent(from_settings=fromSettings, bg=not fromSettings)
        if fromSettings:
            kodiutil.ADDON.openSettings()
    elif arg == 'feature.setRatingBumperStyle':
        pseutil.setRatingBumperStyle()
    elif arg == 'pastebin.paste.log':
        settings.pasteLog()
        kodiutil.ADDON.openSettings()
    elif arg == 'pastebin.delete.key':
        settings.deleteUserKey()
    elif arg == 'reset.database':
        settings.removeContentDatabase()
    elif arg == 'trailer.scrapers':
        settings.setScrapers()
    elif arg == 'test.actions':
        settings.testEventActions(args[0])
    elif arg == 'install.contextMenu':
        settings.installContextMenu()
    elif arg == 'import.cvfiles':
        settings.importCVfiles()
    elif str(arg).startswith('sequence.'):
        settings.setDefaultSequence(arg)
    else:
        main.main()
