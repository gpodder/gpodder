import QtQuick 1.1
import QtDesktop 0.1

import "config.js" as Config

TableView {
  id: treeview
  property int padding: Config.smallSpacing

  TableColumn {
    role: "modelData"
    width: checkboxWidth
    delegate: CheckBox {
      checked: itemValue.qchecked
      clip: true
      onClicked: itemValue.setChecked(checked)
    }
  }

  TableColumn {
    role: "modelData"
    width: parent.width
    delegate: Item{
      height: title.height + description.height + padding
      clip: true

      Label {
        id: title
        anchors.bottom: parent.verticalCenter
        text: itemValue.qtitle
        font.bold: true
        clip: true
      }

      Label {
        id: description
        anchors.top: parent.verticalCenter
        text: itemValue.qdescription
        clip: true
      }
    }
  }
}
