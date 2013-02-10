import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

Window {
  id: addpodcast
  property variant myController: undefined

  width: Config.windowWidth
  height: Config.windowHeight

  Text {
    id: label_add
    text: Util._("URL:")
    anchors.left: parent.left
    anchors.verticalCenter: entry_url.verticalCenter
  }

  TextField {
    id: entry_url
    anchors.right: btn_paste.left
    anchors.left: label_add.right
    anchors.verticalCenter: parent.verticalCenter
  }

  ToolButton {
    id: btn_paste
    text: iconName ? "" : Util._("Paste")
    iconName: "edit-paste"
    anchors.right: parent.right
    anchors.verticalCenter: parent.verticalCenter
  }

  ToolButton {
    id: btn_add
    text: iconName ? "" : Util._("Add")
    iconName: "list-add"
    anchors.bottom: parent.bottom
    anchors.right: parent.right
    onClicked: {
      controller.addSubscriptions(entry_url.text)
      addpodcast.destroy()
    }
  }

  ToolButton {
    id: btn_close
    text: iconName ? "" : Util._("Cancel")
    iconName: "window-close"
    anchors.right: btn_add.left
    anchors.bottom: parent.bottom
    onClicked: myController.close()
  }
}
