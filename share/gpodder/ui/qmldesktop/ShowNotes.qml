import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

Window {
  id: showNotes
  property variant myController: undefined

  width: Config.windowWidth
  height: Config.windowHeight

  TextArea {
    id: textarea1
    anchors.bottom: download_progress.top
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: parent.top
  }

  ProgressBar {
    id: download_progress
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.bottom: buttonrow1.top
  }

  ButtonRow {
    id: buttonrow1
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.left: parent.left

    Button {
      id: flattr_button
      text: Util._("Flattr this")
    }

    Image {
      id: image1
      width: 100
      height: flattr_button.height
      source: "qrc:/qtquickplugin/images/template_image.png"
    }

    Button {
      id: btnPlay
      text: Util._("Play")
    }

    Button {
      id: btnDownload
      text: Util._("&Download")
    }

    Button {
      id: btnCancel
      text: Util._("C&ancel download")
    }

    Button {
      id: btnClose
      text: Util._("Close")
      onClicked: myController.close()
    }
  }
}
