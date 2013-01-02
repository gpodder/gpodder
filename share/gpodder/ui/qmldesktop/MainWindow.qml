import QtQuick 1.1
import QtDesktop 0.1

ApplicationWindow {
  id: mainwindow
  width: 600
  height: 400
  visible: true

  property variant main: mainwindow

  property alias podcastModel: channels.model
  property alias episodeModel: avaliableEpisodes.model
  //property alias showNotesEpisode: showNotes.episode
 /// //property variant currentPodcast: undefined
  //property bool hasPodcasts: podcastList.hasItems
  //property alias currentFilterText: avaliableEpisodes.currentFilterText

  //property bool canGoBack: (main.state != 'podcasts' || contextMenu.state != 'closed' || mediaPlayer.visible) && !progressIndicator.opacity
  //property bool hasPlayButton: nowPlayingThrobber.shouldAppear && !progressIndicator.opacity
 // property bool hasSearchButton: (contextMenu.state == 'closed' && main.state == 'podcasts') && !mediaPlayer.visible && !progressIndicator.opacity
  //property bool hasFilterButton: state == 'episodes' && !mediaPlayer.visible

  property int splitterLimit: 100

  function _(x){
    return controller.translate(x)
  }

  GpodderMenu{}

  ToolBar {
    id: toolbar
    anchors.right: parent.right
    anchors.left: parent.left

    ToolButton {
      id: toolDownload
      text: _("Download")
      anchors.left: parent.left
      anchors.verticalCenter: parent.verticalCenter
    }

    ToolButton {
      id: toolPlay
      text: _("Play")
      anchors.left: toolDownload.right
      anchors.verticalCenter: parent.verticalCenter
      onClicked: controller.onPlayback
    }

    ToolButton {
      id: toolCancel
      text: _("Cancel")
      anchors.left: toolPlay.right
      anchors.verticalCenter: parent.verticalCenter
    }

    ToolButton {
      id: toolPreferences
      text: _("Preferences")
      anchors.left: toolCancel.right
      anchors.verticalCenter: parent.verticalCenter
    }

    ToolButton {
      id: toolQuit
      text: _("Quit")
      anchors.left: toolPreferences.right
      anchors.verticalCenter: parent.verticalCenter
      onClicked: controller.quit()
    }
  }

  TabFrame {
    id: hboxContainer
    current: 0
    anchors.top: toolbar.bottom
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.left: parent.left

    Tab {
      id: podcasts
      anchors.fill: parent
      title: _("Podcasts")

      SplitterRow {
        id: item2
        anchors.fill: parent

        Item {
          id: podcastGroup
          width: 300
          anchors.bottom: parent.bottom
          anchors.left: parent.left
          anchors.top: parent.top
          Splitter.minimumWidth: splitterLimit

          ScrollArea {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: entry_search_podcasts.top

            PodcastList {
              id: channels
              anchors.top: parent.top
              anchors.left: parent.left
              anchors.right: parent.right
            }
          }

          Button {
            id: btnUpdateFeeds
            text: _("Check for new episodes")
            anchors.bottom: pbFeedUpdate.top
            anchors.left: parent.left
            anchors.right: parent.right
          }

          ProgressBar {
            id: pbFeedUpdate
            anchors.right: btnCancelFeedUpdate.left
            anchors.left: parent.left
            anchors.bottom: parent.bottom
          }

          Button {
            id: btnCancelFeedUpdate
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.verticalCenter: pbFeedUpdate.verticalCenter
          }

          TextField {
            id: entry_search_podcasts
            anchors.right: button_search_podcasts_clear.left
            anchors.bottom: btnUpdateFeeds.top
            anchors.left: parent.left
          }

          Button {
            id: button_search_podcasts_clear
            iconSource: ""
            anchors.right: parent.right
            anchors.verticalCenter: entry_search_podcasts.verticalCenter
          }
        }

        Item {
          id: episodesGroup
          width: 200
          anchors.bottom: parent.bottom
          anchors.top: parent.top
          anchors.right: parent.right
          Splitter.minimumWidth: splitterLimit

          ScrollArea {
            id: scrollarea1
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: entry_search_episodes.top

            EpisodeList {
              id: avaliableEpisodes
              anchors.top: parent.top
              anchors.bottom: parent.bottom
              anchors.left: parent.left
              anchors.right: parent.right
            }
          }

          Button {
            id: button_search_episodes_clear
            anchors.right: parent.right
            anchors.verticalCenter: entry_search_episodes.verticalCenter
          }

          TextField {
            id: entry_search_episodes
            anchors.left: label_search_episodes.right
            anchors.right: button_search_episodes_clear.left
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 50
          }

          Text {
            id: label_search_episodes
            text: _("Filter:")
            anchors.left: parent.left
            verticalAlignment: Text.AlignVCenter
            anchors.verticalCenter: button_search_episodes_clear.verticalCenter
          }
        }
      }
    }

    Tab {
      id: progress
      anchors.fill: parent
      title: _("Progress")

      ListView {
        id: progressList
        anchors.bottom: hboxDownloadSettings.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
      }

      Flow {
        id: hboxDownloadSettings
        spacing: 10
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        CheckBox {
          id: cbLimitDownloads
          text: _("Limit rate to")
        }

        SpinBox {
          id: spinLimitDownloads
          width: Math.ceil(Math.log(spinLimitDownloads.value)/Math.log(10))*10+70

          maximumValue: 1073741824
          value: 500
          postfix: _("KiB/s")
        }

        CheckBox {
          id: cbMaxDownloads
          text: _("Limit downloads to")
          checked: true
        }

        SpinBox {
          id: spinMaxDownloads
          maximumValue: 1000
          minimumValue: 1
        }
      }
    }
  }
}
