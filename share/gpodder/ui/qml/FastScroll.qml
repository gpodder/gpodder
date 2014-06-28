import QtQuick 1.1

import 'config.js' as Config

Item {
    id: fastScroll
    property variant flickable: undefined
    property bool available: flickable.contentHeight > 2 * flickable.height
    property real buttonSize: Config.iconSize * 2

    anchors.fill: flickable

    Rectangle {
        id: vorhang
        color: 'black'
        anchors.fill: parent
        opacity: 0
    }

    Rectangle {
        color: 'black'

        anchors {
            right: parent.right
            top: parent.top
            rightMargin: Config.smallSpacing * 2
        }

        width: fastScroll.buttonSize
        height: fastScroll.buttonSize

        opacity: fastScroll.available && flickable.moving && !flickable.atYBeginning
        Behavior on opacity { PropertyAnimation { duration: 100 } }

        Image {
            anchors.centerIn: parent
            source: 'image://theme/icon-m-toolbar-up-selected'
        }

        SequentialAnimation {
            id: scrollToBeginningAnimation

            ParallelAnimation {
                PropertyAnimation {
                    target: vorhang
                    property: 'opacity'
                    to: 1
                }

                PropertyAnimation {
                    target: flickable
                    property: 'contentY'
                    to: flickable.contentY - flickable.height / 2
                }
            }

            ScriptAction {
                script: flickable.contentY = flickable.height / 2;
            }

            ParallelAnimation {
                PropertyAnimation {
                    alwaysRunToEnd: true
                    target: vorhang
                    property: 'opacity'
                    to: 0
                }

                PropertyAnimation {
                    easing.type: Easing.OutExpo
                    target: flickable
                    property: 'contentY'
                    to: 0
                }
            }

            ScriptAction {
                script: vorhang.opacity = 0
            }
        }

        MouseArea {
            enabled: parent.opacity
            anchors.fill: parent
            onClicked: {
                scrollToBeginningAnimation.start()
            }
        }
    }

    Rectangle {
        color: 'black'

        anchors {
            right: parent.right
            bottom: parent.bottom
            rightMargin: Config.smallSpacing * 2
        }

        width: fastScroll.buttonSize
        height: fastScroll.buttonSize

        opacity: fastScroll.available && flickable.moving && !flickable.atYEnd
        Behavior on opacity { PropertyAnimation { duration: 100 } }

        Image {
            anchors.centerIn: parent
            source: 'image://theme/icon-m-toolbar-down-selected'
        }

        SequentialAnimation {
            id: scrollToEndAnimation

            ParallelAnimation {
                PropertyAnimation {
                    target: vorhang
                    property: 'opacity'
                    to: 1
                }

                PropertyAnimation {
                    target: flickable
                    property: 'contentY'
                    to: flickable.contentY + flickable.height / 2
                }
            }

            ScriptAction {
                script: flickable.contentY = flickable.contentHeight - flickable.height - flickable.height / 2;
            }

            ParallelAnimation {
                PropertyAnimation {
                    alwaysRunToEnd: true
                    target: vorhang
                    property: 'opacity'
                    to: 0
                }

                PropertyAnimation {
                    easing.type: Easing.OutExpo
                    target: flickable
                    property: 'contentY'
                    to: flickable.contentHeight - flickable.height
                }
            }

            ScriptAction {
                script: vorhang.opacity = 0
            }
        }

        MouseArea {
            enabled: parent.opacity
            anchors.fill: parent
            onClicked: {
                scrollToEndAnimation.start()
            }
        }
    }
}
