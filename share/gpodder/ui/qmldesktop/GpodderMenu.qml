import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

MenuBar {
  id: menuBar
  property GpodderToolBar toolbarAlias: undefined
  property variant currentEpisode: undefined

  Menu {
    text: Util._("&Podcasts")

    MenuItem {
      text: Util._("Check for new episodes")
      iconName: "view-refresh"
      onTriggered: controller.updateAllPodcasts()
    }

    MenuItem {
      text: Util._("Download new episodes")
      iconName: "download"
      onTriggered: itemDownloadAllNew
    }

    MenuItem {
      text: Util._("Delete episodes")
      iconName: "edit-delete"
      onTriggered: itemRemoveOldEpisodes
    }

    Separator {}

    MenuItem {
      text: Util._("Preferences")
      onTriggered: controller.createWindow(parent, "Preferences.qml")
      iconName: "preferences-system"
    }

    Separator {}

    MenuItem {
      text: Util._("Quit")
      onTriggered: controller.quit()
      iconName: "application-exit"
    }
  }

  Menu {
    text: Util._("&Subscriptions")

    MenuItem {
      text: Util._("Discover new podcasts")
      iconName: "edit-find"
      onTriggered: controller.createWindow(parent, "PodcastDirectory.qml")
    }

    MenuItem {
      text: Util._("Add podcast via URL")
      iconName: "list-add"
      onTriggered: controller.createWindow(parent, "AddPodcast.qml")
    }

    MenuItem {
      text: Util._("Remove podcasts")
      iconName: "list-remove"
      onTriggered: itemMassUnsubscribe
    }

    Separator {}

    MenuItem {
      text: Util._("Update podcast")
      iconName: "view-refresh"
      onTriggered: itemUpdateChannel
    }

    MenuItem {
      text: Util._("Podcast settings")
      iconName: "document-edit"
      onTriggered: controller.createWindow(parent, "PodcastSettings.qml")
    }

    Separator {}

    MenuItem {
      text: Util._("Import from OPML file")
      iconName: "document-open"
      onTriggered: item_import_from_file
    }

    MenuItem {
      text: Util._("Export to OPML file")
      iconName: "document-save-as"
      onTriggered: itemExportChannels
    }
  }

  Menu {
    text: Util._("&Episodes")

    MenuItem {
      text: Util._("Play")
      iconName: "media-playback-start"

      enabled: (currentEpisode!==undefined) ? (currentEpisode.qdownloaded) : false
      onTriggered: controller.playback_selected_episodes(currentEpisode)
    }

    MenuItem {
      text: Util._("Open")
      onTriggered: itemOpenSelected
    }

    MenuItem {
      text: Util._("Download")
      iconName: "download"

      enabled: (currentEpisode!==undefined) ? (!currentEpisode.qdownloaded && !currentEpisode.qdownloading) : false
      onTriggered: controller.downloadEpisode(currentEpisode)
    }

    MenuItem {
      text: Util._("Cancel")
      iconName: "dialog-cancel"

      enabled: (currentEpisode!==undefined) ? (!currentEpisode.qdownloaded && currentEpisode.qdownloading) : false
      onTriggered: controller.cancelDownload(currentEpisode)
    }

    MenuItem {
      text: Util._("Delete")
      iconName: "edit-delete"
      onTriggered: itemDeleteSelected
    }

    Separator {}

    MenuItem {
      text: Util._("Toggle new status")
      onTriggered: item_toggle_played
    }

    MenuItem {
      text: Util._("Change delete lock")
      iconName: "dialog-password"
      onTriggered: item_toggle_lock
    }

    Separator {}

    MenuItem {
      text: Util._("Episode details")
      iconName: "dialog-information"
      onTriggered: item_episode_details
    }
  }

  Menu {
    text: Util._("E&xtras")

    MenuItem {
      text: Util._("Sync to device")
      iconName: "sync-synchronizing"
      onTriggered: item_sync
    }
  }

  Menu {
    text: Util._("&View")

    MenuItem {
      text: Util._("\"All episodes\" in podcast list")
      onTriggered: itemShowAllEpisodes
    }

    MenuItem {
      text: Util._("Use sections for podcast list")
      onTriggered: item_podcast_sections
    }

    Separator {}

    MenuItem {
      text: Util._("Toolbar")
      onTriggered: toolbarAlias.toggleVisible()
    }

    MenuItem {
      text: Util._("Episode descriptions")
      onTriggered: itemShowDescription
    }

    Separator {}

    MenuItem {
      text: Util._("All episodes")
      onTriggered: item_view_episodes_all
    }

    MenuItem {
      text: Util._("Hide deleted episodes")
      onTriggered: item_view_episodes_undeleted
    }

    MenuItem {
      text: Util._("Downloaded episodes")
      onTriggered: item_view_episodes_downloaded
    }

    MenuItem {
      text: Util._("Unplayed episodes")
      onTriggered: item_view_episodes_unplayed
    }

    Separator {}

    MenuItem {
      text: Util._("Hide podcasts without episodes")
      onTriggered: item_view_hide_boring_podcasts
    }
  }

  Menu {
    text: Util._("&Help")

    MenuItem {
      text: Util._("User manual")
      iconName: "help-contents"
      onTriggered: Qt.openUrlExternally(Config.wikiPage)
    }

    MenuItem {
      text: Util._("Go to gpodder.net")
      iconName: "go-home"
      onTriggered: Qt.openUrlExternally('http://gpodder.net')
    }

    MenuItem {
      text: Util._("Software updates")
      iconName: "system-software-update"
      onTriggered: item_check_for_updates
    }

    Separator {}

    MenuItem {
      text: Util._("About")
      iconName: "help-about"
      onTriggered: controller.createWindow(parent, "About.qml")
    }
  }
}
