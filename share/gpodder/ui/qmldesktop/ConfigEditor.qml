import QtQuick 1.1
import QtDesktop 0.1

Window {
  id: configEditor
  width: 400
  height: 300

  Label {
    id: label1
    text: _("Search for:")
    anchors.left: parent.left
    anchors.verticalCenter: entryFilter.verticalCenter
  }

  TextField {
    id: entryFilter
    anchors.top: parent.top
    anchors.left: label1.right
    anchors.right: btnShowAll.left
  }

  Button {
    id: btnShowAll
    text: _("Show All")
    anchors.right: parent.right
    anchors.verticalCenter: entryFilter.verticalCenter
  }

  ScrollArea {
    id: scrollarea1
    anchors.top: entryFilter.bottom
    anchors.bottom: btnClose.top
    anchors.left: parent.left
    anchors.right: parent.right

    ListView {
      id: list_view1
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

  Button {
    id: btnClose
    text: _("Close")
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    onClicked: configEditor.close()
  }
}
