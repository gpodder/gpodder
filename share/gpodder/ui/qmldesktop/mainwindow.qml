import QtQuick 1.1
import QtDesktop 0.1

ApplicationWindow {
  id: mainwindow
  width: 600
  height: 400
  visible: true
  property variant main: mainwindow

  GpodderMenu{}

  ToolBar {
    id: toolbar
    anchors.right: parent.right
    anchors.left: parent.left

    ToolButton {
      id: toolPlay
      text: "Play"
      anchors.left: toolDownload.right
      anchors.verticalCenter: parent.verticalCenter
    }

    ToolButton {
      id: toolCancel
      text: "Cancel"
      anchors.left: toolPlay.right
      anchors.verticalCenter: parent.verticalCenter
    }

    ToolButton {
      id: toolQuit
      text: ""
      anchors.left: toolPreferences.right
      anchors.verticalCenter: parent.verticalCenter
    }

    ToolButton {
      id: toolPreferences
      text: ""
      anchors.left: toolCancel.right
      anchors.verticalCenter: parent.verticalCenter
    }

    ToolButton {
      id: toolDownload
      text: "Download"
      anchors.left: parent.left
      anchors.verticalCenter: parent.verticalCenter
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
      title: qsTr("Podcasts")

      SplitterRow {
        //Item{
        id: item2
        anchors.fill: parent

        Item {
          id: podcastGroup
          width: 300
          anchors.bottom: parent.bottom
          anchors.left: parent.left
          anchors.top: parent.top
          Splitter.minimumWidth: 100

          ScrollArea {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: entry_search_podcasts.top

            ListView {
              id: channels
              anchors.top: parent.top
              anchors.left: parent.left
              anchors.right: parent.right
              delegate: Item {
                height: 40
                Row {
                  id: row1
                  spacing: 10
                  Rectangle {
                    width: 40
                    height: 40
                    color: colorCode
                  }

                  Text {
                    text: name
                    anchors.verticalCenter: parent.verticalCenter
                    font.bold: true
                  }
                }
              }
              model: ListModel {
                ListElement {
                  name: "Grey"
                  colorCode: "grey"
                }

                ListElement {
                  name: "Red"
                  colorCode: "red"
                }

                ListElement {
                  name: "Blue"
                  colorCode: "blue"
                }

                ListElement {
                  name: "Green"
                  colorCode: "green"
                }
              }
            }
          }

          Button {
            id: btnUpdateFeeds
            text: qsTr("Check for new episodes")
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
          Splitter.minimumWidth: 100

          ScrollArea {
            id: scrollarea1
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: entry_search_episodes.top
            ListView {
              id: avaliableEpisodes
              anchors.top: parent.top
              anchors.bottom: parent.bottom
              anchors.left: parent.left
              anchors.right: parent.right

              delegate: Item {
                height: 40
                Row {
                  id: row2
                  spacing: 10
                  Rectangle {
                    width: 40
                    height: 40
                    color: colorCode
                  }

                  Text {
                    text: name
                    anchors.verticalCenter: parent.verticalCenter
                    font.bold: true
                  }
                }
              }
              model: ListModel {
                ListElement {
                  name: "Grey"
                  colorCode: "grey"
                }

                ListElement {
                  name: "Red"
                  colorCode: "red"
                }

                ListElement {
                  name: "Blue"
                  colorCode: "blue"
                }

                ListElement {
                  name: "Green"
                  colorCode: "green"
                }
              }
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
            text: qsTr("Filter:")
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
      title: qsTr("Progress")

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
          text: qsTr("Limit rate to")
        }

        SpinBox {
          id: spinLimitDownloads
          width: Math.ceil(Math.log(spinLimitDownloads.value)/Math.log(10))*10+70

          maximumValue: 1073741824
          value: 500
          postfix: qsTr("KiB/s")
        }

        CheckBox {
          id: cbMaxDownloads
          text: qsTr("Limit downloads to")
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
