import QtQuick 2.15
import QtQuick.Controls 2.15
import "." 1.0

Button {
    property color tint: Theme.clrAccent
    implicitHeight: 34
    contentItem: Text {
        text: parent.text
        color: "#ffffff"
        font.pixelSize: 12
        font.weight: Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        color: parent.down    ? Qt.darker(tint, 1.35)
             : parent.hovered ? Qt.lighter(tint, 1.18)
             :                  tint
        radius: 6
        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
