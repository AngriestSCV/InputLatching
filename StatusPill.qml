import QtQuick 2.15
import QtQuick.Controls 2.15
import "." 1.0

Rectangle {
    property bool active: false
    property string label: ""
    property color activeColor: Theme.clrGreen
    radius: 12
    implicitWidth: pillRow.implicitWidth + 22
    implicitHeight: 24
    color:        active ? Qt.rgba(activeColor.r, activeColor.g, activeColor.b, 0.16)
                         : Qt.rgba(Theme.clrDim.r, Theme.clrDim.g, Theme.clrDim.b, 0.12)
    border.color: active ? activeColor : Theme.clrBorder
    border.width: 1
    Behavior on color        { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 150 } }
    Row {
        id: pillRow
        anchors.centerIn: parent
        spacing: 5
        Rectangle {
            width: 7; height: 7; radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: active ? activeColor : Theme.clrDim
            Behavior on color { ColorAnimation { duration: 150 } }
        }
        Label {
            text: label
            color: active ? activeColor : Theme.clrDim
            font.pixelSize: 12
            font.weight: Font.Medium
            Behavior on color { ColorAnimation { duration: 150 } }
        }
    }
}
