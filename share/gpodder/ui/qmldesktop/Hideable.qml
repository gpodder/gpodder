import QtQuick 1.1

import 'config.js' as Config
import 'util.js' as Util

Item {
  id: hiddeable
  width: childrenRect.width
  height: childrenRect.height
  property bool aboutToHide: false

  transitions: Transition {
    SequentialAnimation {
      NumberAnimation {
        duration: Config.slowTransition
        properties: "y"
        easing.type: Easing.OutBack
      }
    }
  }
}
