import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

Window {
  property variant myController: undefined

  width: Config.windowWidth
  height: Config.windowHeight

  Label {
    id: labelInstructions
    text: Util._("additional text")
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
      text: Util._("Select all")
    }

    Button {
      id: btnCheckNone
      text: Util._("Select none")
    }
  }

  ButtonRow {
    id: buttonrow2
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.left: parent.left

    Button {
      id: btnRemoveAction
      text: Util._("Remove")
    }

    Button {
      id: btnCancel
      text: Util._("Cancel")
      onClicked: myController.close()
    }

    Button {
      id: btnOK
      text: Util._("OK")
    }
  }
}
