import QtQuick 1.1
import QtDesktop 0.1
import QtWebKit 1.0

import 'config.js' as Config
import 'util.js' as Util

Window {
  property variant myController: undefined

  width: Config.windowWidth
  height: Config.windowHeight

  ScrollArea {
    id: scrolledwindow_web
    anchors.top: parent.top
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.bottom: btn_close.top

    WebView {
      id: web_view
    }
  }

  Button {
    id: btn_close
    text: Util._("Cancel")
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.left: parent.left
    onClicked: myController.close()
  }
}
