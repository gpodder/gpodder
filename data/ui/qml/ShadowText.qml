
import Qt 4.7

Text {
    property color shadowColor: "black"
    property int offsetX: -1
    property int offsetY: -2
    property alias color: innerText.color
    color: shadowColor
    elide: Text.ElideNone

    Text {
        id: innerText
        text: parent.text
        anchors.fill: parent
        font: parent.font
        anchors.leftMargin: parent.offsetX
        anchors.topMargin: parent.offsetY
        elide: parent.elide
        clip: parent.clip
    }

}

