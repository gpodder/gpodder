import QtQuick 1.1
import QtDesktop 0.1
import "util.js" as Util
import "config.js" as Config

MenuBar{
  id: menuBar
  property GpodderToolBar toolbarAlias: undefined

  Menu {
    text: _("&Podcasts")

    MenuItem {
      text: _("Check for new episodes")
      onTriggered: controller.updateAllPodcasts()
    }

    MenuItem {
      text: _("Download new episodes")
      onTriggered: itemDownloadAllNew
    }

    MenuItem {
      text: _("Delete episodes")
      onTriggered: itemRemoveOldEpisodes
    }

    Separator {}

    MenuItem {
      text: _("Preferences")
      onTriggered: Util.createWindow(parent, "Preferences.qml")
    }

    Separator {}

    MenuItem {
      text: _("Quit")
      onTriggered: controller.quit()
    }
  }

  Menu{
    text: _("&Subscriptions")

    MenuItem {
      text: _("Discover new podcasts")
      onTriggered: Util.createWindow(parent, "PodcastDirectory.qml")
    }

    MenuItem {
      text: _("Add podcast via URL")
      onTriggered: Util.createWindow(parent, "AddPodcast.qml")
    }

    MenuItem {
      text: _("Remove podcasts")
      onTriggered: itemMassUnsubscribe
    }

    Separator {}

    MenuItem {
      text: _("Update podcast")
      onTriggered: itemUpdateChannel
    }

    MenuItem {
      text: _("Podcast settings")
      onTriggered: Util.createWindow(parent, "Channel.qml")
    }

    Separator {}

    MenuItem {
      text: _("Import from OPML file")
      onTriggered: item_import_from_file
    }

    MenuItem {
      text: _("Export to OPML file")
      onTriggered: itemExportChannels
    }
  }

  Menu{
    text: _("&Episodes")

    MenuItem {
      text: _("Play")
      onTriggered: itemPlaySelected
    }

    MenuItem {
      text: _("Open")
      onTriggered: itemOpenSelected
    }

    MenuItem {
      text: _("Download")
      onTriggered: itemDownloadSelected
    }

    MenuItem {
      text: _("Cancel")
      onTriggered: item_cancel_download
    }

    MenuItem {
      text: _("Delete")
      onTriggered: itemDeleteSelected
    }

    Separator {}

    MenuItem {
      text: _("Toggle new status")
      onTriggered: item_toggle_played
    }

    MenuItem {
      text: _("Change delete lock")
      onTriggered: item_toggle_lock
    }

    Separator {}

    MenuItem {
      text: _("Episode details")
      onTriggered: item_episode_details
    }
  }

  Menu{
    text: _("E&xtras")

    MenuItem {
      text: _("Sync to device")
      onTriggered: item_sync
    }
  }

  Menu{
    text: _("&View")

    MenuItem {
      text: _("\"All episodes\" in podcast list")
      onTriggered: itemShowAllEpisodes
    }

    MenuItem {
      text: _("Use sections for podcast list")
      onTriggered: item_podcast_sections
    }

    Separator {}

    MenuItem {
      text: _("Toolbar")
      onTriggered: toolbarAlias.toggleVisible()
    }

    MenuItem {
      text: _("Episode descriptions")
      onTriggered: itemShowDescription
    }

    Separator {}

    MenuItem {
      text: _("All episodes")
      onTriggered: item_view_episodes_all
    }

    MenuItem {
      text: _("Hide deleted episodes")
      onTriggered: item_view_episodes_undeleted
    }

    MenuItem {
      text: _("Downloaded episodes")
      onTriggered: item_view_episodes_downloaded
    }

    MenuItem {
      text: _("Unplayed episodes")
      onTriggered: item_view_episodes_unplayed
    }

    Separator {}

    MenuItem {
      text: _("Hide podcasts without episodes")
      onTriggered: item_view_hide_boring_podcasts
    }
  }

  Menu{
    text: _("&Help")

    MenuItem {
      text: _("User manual")
      onTriggered: Qt.openUrlExternally(Config.wikiPage)
    }

    MenuItem {
      text: _("Go to gpodder.net")
      onTriggered: Qt.openUrlExternally('http://gpodder.net')
    }

    MenuItem {
      text: _("Software updates")
      onTriggered: item_check_for_updates
    }

    Separator {}

    MenuItem {
      text: _("About")
      onTriggered: Util.createWindow(parent, "About.qml")
    }
  }
}
