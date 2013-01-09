import QtQuick 1.1
import QtDesktop 0.1

Item {
  id: container
  height: 1 //set to > 0 because of warning at startup

  property int borderWidth: 1
  property int radius: 5
  property alias leftText: labelLeftText.text
  property alias rightText: labelRightText.text
  property int fontSize: height / 2
  property string textColor: "white"

  Rectangle {
    id: rectLeft
    width: parent.width - borderWidth
    height: parent.height - borderWidth
    radius: container.radius
    x: (borderWidth - 1) / 2
    y: (borderWidth - 1) / 2

    color: "#D0D0D0"
    border{
      color: rectRight.color
      width: borderWidth
    }
  }

  Rectangle {
    id: rectRight
    width: (rectLeft.width - borderWidth) / 2
    height: rectLeft.height - container.borderWidth
    radius: container.radius
    anchors {
      left: rectLeft.horizontalCenter
      top: container.top
      topMargin: borderWidth
    }

    color: "#7E7C79"

    //Mask left radius of right rectangle
    Rectangle {
      width: container.radius
      height: rectRight.height
      color: rectRight.color
    }

    Label {
        id: labelRightText
        text: "R"
        font.pointSize: fontSize
        color: textColor
        anchors.centerIn: parent
    }
  }

  Item {
    id: rectLeft2
    width: rectRight.width
    height: rectRight.height

    anchors {
      top: rectRight.top
      right: rectRight.left
    }

    Label {
        id: labelLeftText
        text: "L"
        font.pointSize: fontSize
        color: textColor
        anchors.centerIn: parent
    }
  }
}
