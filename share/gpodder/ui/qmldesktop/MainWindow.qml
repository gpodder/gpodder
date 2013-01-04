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
  property variant currentPodcast: undefined
  property bool hasPodcasts: channels.hasItems
  property alias currentFilterText: avaliableEpisodes.currentFilterText

  //property bool canGoBack: (main.state != 'podcasts' || contextMenu.state != 'closed' || mediaPlayer.visible) && !progressIndicator.opacity
  //property bool hasPlayButton: nowPlayingThrobber.shouldAppear && !progressIndicator.opacity
  // property bool hasSearchButton: (contextMenu.state == 'closed' && main.state == 'podcasts') && !mediaPlayer.visible && !progressIndicator.opacity
  //property bool hasFilterButton: state == 'episodes' && !mediaPlayer.visible

  property int splitterMinWidth: 200
  property int strangeMargin: 20

  function _(x){
    return controller.translate(x)
  }

  GpodderMenu {
    id: menu
    toolbarAlias: toolbar
  }

  GpodderToolBar {
    id: toolbar
  }

  TabFrame {
    id: hboxContainer
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
          anchors.bottom: parent.bottom
          anchors.left: parent.left
          anchors.top: parent.top
          Splitter.minimumWidth: splitterMinWidth

          ScrollArea {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: entry_search_podcasts.top

            PodcastList {
              id: channels
              anchors {
                top: parent.top
                left: parent.left
              }
              width: parent.parent.width - strangeMargin

              onPodcastSelected: {
                controller.podcastSelected(podcast)
                mainwindow.currentPodcast = podcast
              }
              onPodcastContextMenu: controller.podcastContextMenu(podcast)
              onSubscribe: contextMenu.showSubscribe()
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
          Splitter.minimumWidth: splitterMinWidth

          ScrollArea {
            id: scrollarea1
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: episodesFilterBox.top

            EpisodeList {
              id: avaliableEpisodes
              anchors.top: parent.top
              anchors.left: parent.left
              width: parent.parent.width - strangeMargin

              Keys.onPressed: {
                d.text = event.key
              }

              onModelChanged: {
                currentFilterText.text = ""
              }
            }
          }

          Item {
            id: episodesFilterBox
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.bottomMargin: toolbar.height

            Text {
              id: label_search_episodes
              text: _("Filter:")
              anchors.left: parent.left
              verticalAlignment: Text.AlignVCenter
              anchors.verticalCenter: button_search_episodes_clear.verticalCenter
            }

            TextField {
              id: currentFilterText
              anchors.left: label_search_episodes.right
              anchors.right: button_search_episodes_clear.left
              anchors.bottom: parent.bottom
            }

            Button {
              id: button_search_episodes_clear
              anchors.right: parent.right
              anchors.verticalCenter: currentFilterText.verticalCenter
            }
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
