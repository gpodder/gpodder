import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

Item {
  id: rectangle1
  width: 400
  height: 300

  property alias message: message.text
  property alias inputText: inputText.text

  Label {
    id: message
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.verticalCenter: parent.verticalCenter

    visible: text.length > 0
  }

  TextField {
    id: inputText
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.verticalCenter: parent.verticalCenter

    visible: text.length > 0
  }

  ButtonRow {
    id: buttonrow1
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.bottom: parent.bottom

    Button {
      id: button1
      text: Util._("Ok")
      anchors.left: parent.left
    }

    Button {
      id: button2
      text: Util._("Cancel")
      anchors.right: parent.right
    }
  }
}
