import QtQuick 1.1

Item {
  property int  padding: 0
  property alias text: textContent.text
  property alias fontBold: textContent.font.bold

  height: children[0].height + padding * 2
  clip: true

  Text {
    id: textContent
    clip: true
    anchors.verticalCenter: parent.verticalCenter
    width: parent.width - padding
  }
}
