import QtQuick 1.1
import QtDesktop 0.1

Window {
  width: 400
  height: 300

  TabFrame {
    id: tabgroup1
    anchors.bottom: buttonrow1.top
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: parent.top

    TabBar {
      id: tabbar1
      anchors.fill: parent
      property string title: _("&OPML/Search")

      TextField {
        id: entryURL
        anchors.right: btnDownloadOpml.left
        anchors.left: parent.left
        anchors.top: parent.top
      }

      Button {
        id: btnDownloadOpml
        text: _("Download")
        anchors.right: parent.right
        anchors.verticalCenter: entryURL.verticalCenter
      }

      ScrollArea {
        id: scrollarea2
        anchors.top: entryURL.bottom
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.left: parent.left

        ListView {
          id: treeviewChannelChooser
          height: 160
          delegate: Item {
            x: 5
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
    }


    ScrollArea {
      id: scrollarea1
      anchors.fill: parent
      property string title: _("Top &podcasts")

      ListView {
        id: treeviewTopPodcastsChooser
        height: 160
        delegate: Item {
          x: 5
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

    TabBar {
      id: tabbar2
      anchors.fill: parent
      property string title: _("&YouTube")

      TextField {
        id: entryYoutubeSearch
        anchors.right: btnSearchYouTube.left
        anchors.top: parent.top
        anchors.left: parent.left
      }

      Button {
        id: btnSearchYouTube
        text: _("Search")
        anchors.right: parent.right
        anchors.verticalCenter: entryYoutubeSearch.verticalCenter
      }

      ScrollArea {
        id: scrollarea3
        anchors.top: entryYoutubeSearch.bottom
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.left: parent.left

        ListView {
          id: treeviewYouTubeChooser
          height: 160
          delegate: Item {
            x: 5
            height: 40
            Row {
              id: row3
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
    }
  }

  ButtonRow {
    id: buttonrow1
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.left: parent.left

    Button {
      id: btnSelectAll
      text: _("Select All")
    }

    Button {
      id: btnSelectNone
      text: _("Select None")
    }

    Button {
      id: btnCancel
      text: _("Cancel")
    }

    Button {
      id: btnOK
      text: _("Add")
    }
  }
}
