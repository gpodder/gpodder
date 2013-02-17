import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

ApplicationWindow {
  id: mainwindow
  width: Config.windowWidth
  height: Config.windowHeight
  visible: true
  SystemPalette {id: syspal}

  property alias podcastModel: channels.model
  property alias episodeModel: avaliableEpisodes.model
  //property alias showNotesEpisode: showNotes.episode
  property variant currentPodcast: undefined
  property variant currentEpisode: undefined
  property bool hasPodcasts: channels.hasItems
  property alias currentFilterText: avaliableEpisodes.currentFilterText

  //property bool canGoBack: (main.state != 'podcasts' || contextMenu.state != 'closed' || mediaPlayer.visible) && !progressIndicator.opacity
  //property bool hasPlayButton: nowPlayingThrobber.shouldAppear && !progressIndicator.opacity
  //property bool hasSearchButton: (contextMenu.state == 'closed' && main.state == 'podcasts') && !mediaPlayer.visible && !progressIndicator.opacity
  //property bool hasFilterButton: state == 'episodes' && !mediaPlayer.visible

  property int splitterMinWidth: 200
  property int splitterMinHeight: 200
  property int strangeMargin: 20
  property int bottomMarginHack: 20

  function startProgress(message, progress){
    pbFeedUpdate.value = progress
    console.log(progress)
  }

  function endProgress(){
    pbFeedUpdate.value = 0
  }

  function showInputDialog(message, value, accept, reject, textInput) {
      inputDialogText.text = message
      inputDialogField.text = value
      inputDialogAccept.text = accept
      inputDialogReject.text = reject
      inputDialogField.visible = textInput

      if (textInput) {
          inputSheet.open()
      } else {
          queryDialog.open()
      }
  }

  GpodderMenu {
    id: menu
    toolbarAlias: toolbar
    currentEpisode: mainwindow.currentEpisode
  }

  GpodderToolBar {
    id: toolbar
    currentEpisode: mainwindow.currentEpisode
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
      title: Util._("Podcasts")

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
            anchors.verticalCenter: button_search_podcasts_clear.verticalCenter
            anchors.left: parent.left
          }

          ToolButton {
            id: button_search_podcasts_clear
            iconName: "edit-clear"
            text: iconName ? "" : Util._("Clear")
            anchors.right: parent.right
            anchors.bottom: btnUpdateFeeds.top
            onClicked: entry_search_podcasts.text = ""
          }

          Button {
            id: btnUpdateFeeds
            text: Util._("Check for new episodes")
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

            ToolButton {
              id: btnCancelFeedUpdate
              text: iconName ? "" : Util._("Cancel")
              enabled: pbFeedUpdate.value
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              iconName: "dialog-cancel"
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

            EpisodeList {
              Splitter.minimumHeight: splitterMinHeight
              id: avaliableEpisodes
              width: episodesGroup.width - strangeMargin

              onModelChanged: episodeFilter.text = ""
              onEpisodeItemChange: mainwindow.currentEpisode = episode
              onActivateFilter: episodeFilter.focus = true
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
            height: Math.max(label_search_episodes.height, episodeFilter.height, episodeFilterClear.height)
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            Text {
              id: label_search_episodes
              text: Util._("Filter:")
              anchors.left: parent.left
              verticalAlignment: Text.AlignVCenter
              anchors.verticalCenter: parent.verticalCenter
            }

            TextField {
              id: episodeFilter
              anchors.left: label_search_episodes.right
              anchors.right: episodeFilterClear.left
              anchors.verticalCenter: parent.verticalCenter
              onTextChanged: controller.setEpisodeFilter(text)
            }

            ToolButton{
              id: episodeFilterClear
              text: iconName ? "" : Util._("Clear")
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              onClicked: episodeFilter.text = ""
              iconName:  "edit-clear"
            }
          }
        }
      }
    }

    Tab {
      id: progress
      anchors.fill: parent
      title: Util._("Progress")

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
          text: Util._("Limit rate to")
        }

        SpinBox {
          id: spinLimitDownloads
          width: Math.ceil(Math.log(spinLimitDownloads.value)/Math.log(10))*10+70

          maximumValue: 1073741824
          value: 500
          postfix: Util._("KiB/s")
        }

        CheckBox {
          id: cbMaxDownloads
          text: Util._("Limit downloads to")
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
