import QtQuick 1.1
import QtDesktop 0.1

ApplicationWindow {
  id: mainwindow
  width: 640
  height: 480
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
  property int splitterMinHeight: 200
  property int strangeMargin: 20
  property int bottomMarginHack: 20

  function _(x){
    return controller.translate(x)
  }

  function startProgress(message, progress){
    pbFeedUpdate.value = progress
    console.log(progress)
  }

  function endProgress(){
    pbFeedUpdate.value = 0
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
    anchors{
      top: toolbar.bottom
      right: parent.right
      bottom: parent.bottom
      left: parent.left
      bottomMargin: bottomMarginHack
    }

    Tab {
      id: podcasts
      anchors {
        fill: parent
      }
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
              width: podcastGroup.width - strangeMargin

              onPodcastSelected: {
                controller.podcastSelected(podcast)
                mainwindow.currentPodcast = podcast
              }
              onPodcastContextMenu: controller.podcastContextMenu(podcast)
              onSubscribe: contextMenu.showSubscribe()
            }
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
            text: _("Clear")
            anchors.right: parent.right
            anchors.verticalCenter: entry_search_podcasts.verticalCenter
          }

          Button {
            id: btnUpdateFeeds
            text: _("Check for new episodes")
            anchors.bottom: progressRow.top
            anchors.left: parent.left
            anchors.right: parent.right
            onClicked: controller.updateAllPodcasts()
          }

          Hideable {
            id: progressRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            ProgressBar {
              id: pbFeedUpdate
              anchors.left: parent.left
              anchors.right: btnCancelFeedUpdate.left
              anchors.verticalCenter: parent.verticalCenter
            }

            Button {
              id: btnCancelFeedUpdate
              text: _("Cancel")
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
            }
          }
        }

        Item {
          id: episodesGroup
          anchors.right: parent.right
          anchors.top: parent.top
          anchors.bottom: parent.bottom
          Splitter.minimumWidth: splitterMinWidth

          SplitterColumn {
            anchors {
              top: parent.top
              right: parent.right
              bottom: episodesFilterBox.top
            }
            width: parent.width

            ScrollArea {
              id: scrollarea1
              anchors.top: parent.top
              width: parent.width
              Splitter.minimumHeight: splitterMinHeight

              EpisodeList {
                id: avaliableEpisodes
                anchors.top: parent.top
                anchors.left: parent.left
                width: episodesGroup.width - strangeMargin

                onModelChanged: currentFilterText.text = ""
                onEpisodeItemChange: toolbar.episode = episode
                onActivateFilter: currentFilterText.focus = true
              }
            }

            TextArea {
              id: description
              text: avaliableEpisodes.description
              readOnly: true
              width: parent.width

              anchors {
                bottom: parent.bottom
              }
              clip: true
            }
          }

          Item {
            id: episodesFilterBox
            height: childrenRect.height
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

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

              //              onTextChanged: controller.
            }

            Button {
              id: button_search_episodes_clear
              text: _("Clear")
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
