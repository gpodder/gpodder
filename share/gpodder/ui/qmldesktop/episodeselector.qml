import QtQuick 1.1
import QtDesktop 0.1

Window {
  width: 400
  height: 300

  Label {
    id: labelInstructions
    text: qsTr("additional text")
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: parent.top
  }

  ScrollArea {
    id: scrollarea1
    anchors.top: labelInstructions.bottom
    anchors.right: parent.right
    anchors.bottom: buttonrow1.top
    anchors.left: parent.left

    ListView {
      id: treeviewEpisodes
      height: count*40
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

  ButtonRow {
    id: buttonrow1
    anchors.right: parent.right
    anchors.bottom: buttonrow2.top
    anchors.left: parent.left

    Button {
      id: btnCheckAll
      text: "Select all"
    }

    Button {
      id: btnCheckNone
      text: "Select none"
    }
  }

  ButtonRow {
    id: buttonrow2
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.left: parent.left

    Button {
      id: btnRemoveAction
      text: "Remove"
    }

    Button {
      id: btnCancel
      text: "Cancel"
    }

    Button {
      id: btnOK
      text: "OK"
    }
  }
}
