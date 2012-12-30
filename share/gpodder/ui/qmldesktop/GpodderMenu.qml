import QtQuick 1.1
import QtDesktop 0.1

MenuBar{
  Menu {
    text: "&Podcasts"

    MenuItem {
      text:"Check for new episodes"
      onTriggered: itemUpdate
    }

    MenuItem {
      text:"Download new episodes"
      onTriggered: itemDownloadAllNew
    }

    MenuItem {
      text:"Delete episodes"
      onTriggered: itemRemoveOldEpisodes
    }

    Separator {}

    MenuItem {
      text:"Preferences"
      onTriggered: itemPreferences
    }

    Separator {}

    MenuItem {
      text:"Quit"
      onTriggered: Qt.quit()
    }
  }

  Menu{
    text: "&Subscriptions"

    MenuItem {
      text:"Discover new podcasts"
      onTriggered: itemFind
    }

    MenuItem {
      text:"Add podcast via URL"
      onTriggered: itemAddChannel
    }

    MenuItem {
      text:"Remove podcasts"
      onTriggered: itemMassUnsubscribe
    }

    Separator {}

    MenuItem {
      text:"Update podcast"
      onTriggered: itemUpdateChannel
    }

    MenuItem {
      text:"Podcast settings"
      onTriggered: itemEditChannel
    }

    Separator {}

    MenuItem {
      text:"Import from OPML file"
      onTriggered: item_import_from_file
    }

    MenuItem {
      text:"Export to OPML file"
      onTriggered: itemExportChannels
    }
  }

  Menu{
    text: "&Episodes"

    MenuItem {
      text:"Play"
      onTriggered: itemPlaySelected
    }

    MenuItem {
      text:"Open"
      onTriggered: itemOpenSelected
    }

    MenuItem {
      text:"Download"
      onTriggered: itemDownloadSelected
    }

    MenuItem {
      text:"Cancel"
      onTriggered: item_cancel_download
    }

    MenuItem {
      text:"Delete"
      onTriggered: itemDeleteSelected
    }

    Separator {}

    MenuItem {
      text:"Toggle new status"
      onTriggered: item_toggle_played
    }

    MenuItem {
      text:"Change delete lock"
      onTriggered: item_toggle_lock
    }

    Separator {}

    MenuItem {
      text:"Episode details"
      onTriggered: item_episode_details
    }
  }

  Menu{
    text: "E&xtras"

    MenuItem {
      text:"Sync to device"
      onTriggered: item_sync
    }
  }

  Menu{
    text: "&View"

    MenuItem {
      text:"\"All episodes\" in podcast list"
      onTriggered: itemShowAllEpisodes
    }

    MenuItem {
      text:"Use sections for podcast list"
      onTriggered: item_podcast_sections
    }

    Separator {}

    MenuItem {
      text:"Toolbar"
      onTriggered: itemShowToolbar
    }

    MenuItem {
      text:"Episode descriptions"
      onTriggered: itemShowDescription
    }

    Separator {}

    MenuItem {
      text:"All episodes"
      onTriggered: item_view_episodes_all
    }

    MenuItem {
      text:"Hide deleted episodes"
      onTriggered: item_view_episodes_undeleted
    }

    MenuItem {
      text:"Downloaded episodes"
      onTriggered: item_view_episodes_downloaded
    }

    MenuItem {
      text:"Unplayed episodes"
      onTriggered: item_view_episodes_unplayed
    }

    Separator {}

    MenuItem {
      text:"Hide podcasts without episodes"
      onTriggered: item_view_hide_boring_podcasts
    }
  }

  Menu{
    text: "&Help"

    MenuItem {
      text:"User manual"
      onTriggered: wiki
    }

    MenuItem {
      text:"Go to gpodder.net"
      onTriggered: item_goto_mygpo
    }

    MenuItem {
      text:"Software updates"
      onTriggered: item_check_for_updates
    }

    Separator {}

    MenuItem {
      text:"About"
      onTriggered: itemAbout
    }
  }
}
