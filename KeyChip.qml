import QtQuick 2.15
import QtQuick.Controls 2.15
import "." 1.0

Rectangle {
    property string keyText: ""
    property color chipColor: Theme.clrAccent
    color:        Qt.rgba(chipColor.r, chipColor.g, chipColor.b, 0.18)
    border.color: Qt.rgba(chipColor.r, chipColor.g, chipColor.b, 0.55)
    border.width: 1
    radius: 5
    width: chipLabel.implicitWidth + 14
    height: 22
    Label {
        id: chipLabel
        anchors.centerIn: parent
        text: keyText
        color: chipColor
        font.pixelSize: 11
        font.weight: Font.Medium
    }
}
