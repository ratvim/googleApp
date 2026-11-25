#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QQuickWebEngineProfile>
#include <QCommandLineParser>
#include <QCommandLineOption>
#include <QIcon>
#include <QFile>
#include <QFileInfo>
#include <QDir>
#include <QStandardPaths>
#include <QProcess>
#include <QtWebEngineQuick/qtwebenginequickglobal.h>
#include <iostream>

static const char *appWindowQml = R"QML(
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

Window {
    id: root
    visible: true
    width: 1100
    height: 750
    minimumWidth: 500
    minimumHeight: 380
    title: appName
    flags: Qt.Window | Qt.FramelessWindowHint
    color: "#181a1f"

    property bool webHeaderHidden: initialHideWebHeader

    // Created Application Bar (Custom Native Header with Window Controls)
    Rectangle {
        id: appHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 38
        color: "#1e222b"
        z: 100

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        DragHandler {
            target: null
            onActiveChanged: if (active) root.startSystemMove()
        }

        TapHandler {
            gesturePolicy: TapHandler.WithinBounds
            onDoubleTapped: {
                if (root.visibility === Window.Maximized) {
                    root.showNormal()
                } else {
                    root.showMaximized()
                }
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 0
            spacing: 8

            // App Icon & Name
            RowLayout {
                spacing: 8
                Image {
                    source: (typeof appIcon !== "undefined" && appIcon && appIcon !== "") ? (appIcon.indexOf("/") === 0 ? "file://" + appIcon : appIcon) : undefined
                    visible: typeof appIcon !== "undefined" && appIcon !== ""
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    fillMode: Image.PreserveAspectFit
                }
                Text {
                    text: appName
                    color: "#e6edf3"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
            }

            // Flexible Spacer for Draggable Header
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            // Window Action Buttons (Minimize, Maximize, Close)
            RowLayout {
                spacing: 0
                Layout.alignment: Qt.AlignRight

                // Minimize
                Rectangle {
                    Layout.preferredWidth: 46; Layout.preferredHeight: 38
                    color: minMouse.containsMouse ? "#2d3342" : "transparent"
                    Text { text: "—"; color: "#c0caf5"; font.pixelSize: 12; anchors.centerIn: parent }
                    MouseArea {
                        id: minMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showMinimized()
                    }
                }

                // Maximize / Restore
                Rectangle {
                    Layout.preferredWidth: 46; Layout.preferredHeight: 38
                    color: maxMouse.containsMouse ? "#2d3342" : "transparent"
                    Text {
                        text: root.visibility === Window.Maximized ? "❐" : "□"
                        color: "#c0caf5"
                        font.pixelSize: 12
                        anchors.centerIn: parent
                    }
                    MouseArea {
                        id: maxMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.visibility === Window.Maximized) {
                                root.showNormal()
                            } else {
                                root.showMaximized()
                            }
                        }
                    }
                }

                // Close
                Rectangle {
                    Layout.preferredWidth: 46; Layout.preferredHeight: 38
                    color: closeMouse.containsMouse ? "#e81123" : "transparent"
                    Text { text: "✕"; color: "#ffffff"; font.pixelSize: 13; anchors.centerIn: parent }
                    MouseArea {
                        id: closeMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }
        }
    }

    // Embedded Web Application View
    WebEngineView {
        id: webView
        anchors.top: appHeader.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        profile: webProfile
        url: (typeof appUrl !== "undefined" && appUrl && appUrl !== "") ? appUrl : undefined

        settings.javascriptEnabled: true
        settings.pluginsEnabled: true
        settings.fullScreenSupportEnabled: true
        settings.localContentCanAccessRemoteUrls: true
        settings.localStorageEnabled: true
        settings.javascriptCanAccessClipboard: true
        settings.allowWindowActivationFromJavaScript: true
        settings.webGLEnabled: true
        settings.accelerated2dCanvasEnabled: true

        function applyTopBarVisibility() {
            var css = "#gb, header#gb, .gb_Fd, #masthead-container, #masthead, ytd-masthead, ytmusic-nav-bar, div[role='banner'], header[role='banner'] { display: none !important; } body, html { margin-top: 0 !important; padding-top: 0 !important; } #content, #page-manager, ytd-app { margin-top: 0 !important; padding-top: 0 !important; }";
            var js = "(function() { var sid = '__googleapp_topbar_style__'; var el = document.getElementById(sid); if (" + (root.webHeaderHidden ? "true" : "false") + ") { if (!el) { el = document.createElement('style'); el.id = sid; el.textContent = " + JSON.stringify(css) + "; document.head.appendChild(el); } } else { if (el) el.remove(); } })();";
            webView.runJavaScript(js);
        }

        onLoadingChanged: function(loadRequest) {
            if (loadRequest.status === WebEngineView.LoadSucceededStatus) {
                applyTopBarVisibility();
            }
        }

        onPermissionRequested: function(request) {
            request.grant();
        }

        onFullScreenRequested: function(request) {
            if (request.toggleOn) {
                root.showFullScreen();
            } else {
                root.showNormal();
            }
            request.accept();
        }

        onNewWindowRequested: function(request) {
            request.openIn(webView);
        }
    }

    // Window Edge Resize Handlers (Borders & Corners)
    MouseArea {
        anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 6; z: 200
        cursorShape: Qt.SizeHorCursor
        onPressed: root.startSystemResize(Qt.LeftEdge)
    }
    MouseArea {
        anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 6; z: 200
        cursorShape: Qt.SizeHorCursor
        onPressed: root.startSystemResize(Qt.RightEdge)
    }
    MouseArea {
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; height: 6; z: 200
        cursorShape: Qt.SizeVerCursor
        onPressed: root.startSystemResize(Qt.TopEdge)
    }
    MouseArea {
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; height: 6; z: 200
        cursorShape: Qt.SizeVerCursor
        onPressed: root.startSystemResize(Qt.BottomEdge)
    }
    MouseArea {
        anchors.top: parent.top; anchors.left: parent.left; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeFDiagCursor
        onPressed: root.startSystemResize(Qt.TopEdge | Qt.LeftEdge)
    }
    MouseArea {
        anchors.top: parent.top; anchors.right: parent.right; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeBDiagCursor
        onPressed: root.startSystemResize(Qt.TopEdge | Qt.RightEdge)
    }
    MouseArea {
        anchors.bottom: parent.bottom; anchors.left: parent.left; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeBDiagCursor
        onPressed: root.startSystemResize(Qt.BottomEdge | Qt.LeftEdge)
    }
    MouseArea {
        anchors.bottom: parent.bottom; anchors.right: parent.right; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeFDiagCursor
        onPressed: root.startSystemResize(Qt.BottomEdge | Qt.RightEdge)
    }

    // Global Shortcuts
    Shortcut { sequence: "F11"; onActivated: root.visibility = (root.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen) }
    Shortcut { sequence: "F5"; onActivated: webView.reload() }
    Shortcut { sequence: "Ctrl+R"; onActivated: webView.reload() }
    Shortcut { sequence: "Alt+Left"; onActivated: if (webView.canGoBack) webView.goBack() }
    Shortcut { sequence: "Alt+Right"; onActivated: if (webView.canGoForward) webView.goForward() }
    Shortcut { sequence: "Ctrl+H"; onActivated: { root.webHeaderHidden = !root.webHeaderHidden; webView.applyTopBarVisibility(); } }
    Shortcut { sequence: "Ctrl+Q"; onActivated: root.close() }
}
)QML";

int main(int argc, char *argv[]) {
    qputenv("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --password-store=basic --disable-blink-features=AutomationControlled");
    QtWebEngineQuick::initialize();

    QGuiApplication app(argc, argv);

    QCommandLineParser parser;
    parser.setApplicationDescription("GoogleApp Standalone Web App Runner");
    parser.addHelpOption();

    QCommandLineOption slugOpt("slug", "Application slug identifier", "slug", "web-app");
    QCommandLineOption nameOpt("name", "Application display name", "name", "Web App");
    QCommandLineOption urlOpt("url", "Application web URL", "url", "https://google.com");
    QCommandLineOption iconOpt("icon", "Application icon file or name", "icon", "");
    QCommandLineOption profileDirOpt("profile-dir", "Custom persistent profile directory path", "path", "");
    QCommandLineOption uaOpt("user-agent", "Custom HTTP User-Agent string", "ua", "");
    QCommandLineOption showHeaderOpt("show-web-header", "Keep the web UI top bar visible by default");

    parser.addOption(slugOpt);
    parser.addOption(nameOpt);
    parser.addOption(urlOpt);
    parser.addOption(iconOpt);
    parser.addOption(profileDirOpt);
    parser.addOption(uaOpt);
    parser.addOption(showHeaderOpt);

    parser.process(app);

    QString slug = parser.value(slugOpt);
    QString name = parser.value(nameOpt);
    QString url = parser.value(urlOpt);
    QString icon = parser.value(iconOpt);
    bool hideWebHeader = !parser.isSet(showHeaderOpt);

    QString desktopId = QString("googleapp-%1").arg(slug);
    app.setDesktopFileName(desktopId);
    app.setApplicationName(name);

    QString resolvedIcon = icon;
    if (!icon.isEmpty()) {
        if (QFile::exists(icon)) {
            app.setWindowIcon(QIcon(icon));
            resolvedIcon = icon;
        } else {
            QIcon themeIcon = QIcon::fromTheme(icon);
            if (!themeIcon.isNull()) {
                app.setWindowIcon(themeIcon);
            }
            QProcess proc;
            proc.start("kiconfinder6", QStringList() << icon);
            if (proc.waitForFinished(800) && proc.exitCode() == 0) {
                QString outPath = QString::fromUtf8(proc.readAllStandardOutput()).trimmed();
                if (!outPath.isEmpty() && QFile::exists(outPath)) {
                    resolvedIcon = outPath;
                }
            }
        }
    }

    // Standardized persistent profile & cache directories
    QString storageDir = parser.value(profileDirOpt);
    if (storageDir.isEmpty()) {
        storageDir = QString("%1/.local/share/googleapp-profiles/%2").arg(QDir::homePath(), desktopId);
    }
    QString cacheDir = QString("%1/.cache/googleapp/%2").arg(QDir::homePath(), desktopId);

    QDir().mkpath(storageDir);
    QDir().mkpath(cacheDir);

    // Explicitly configure disk-backed persistent profile in C++
    QQuickWebEngineProfile profile;
    profile.setStorageName(slug);
    profile.setPersistentStoragePath(storageDir);
    profile.setCachePath(cacheDir);
    profile.setOffTheRecord(false);
    profile.setPersistentCookiesPolicy(QQuickWebEngineProfile::AllowPersistentCookies);
    profile.setPersistentPermissionsPolicy(QQuickWebEngineProfile::PersistentPermissionsPolicy::StoreOnDisk);
    profile.setHttpCacheType(QQuickWebEngineProfile::DiskHttpCache);
    QString userAgent = parser.value(uaOpt);
    if (userAgent.isEmpty()) {
        // Modern Firefox User-Agent: bypasses Google's embedded WebView / "This browser or app may not be secure" block
        userAgent = "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0";
    }
    profile.setHttpUserAgent(userAgent);

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("webProfile", &profile);
    engine.rootContext()->setContextProperty("appSlug", slug);
    engine.rootContext()->setContextProperty("appName", name);
    engine.rootContext()->setContextProperty("appUrl", url);
    engine.rootContext()->setContextProperty("appIcon", resolvedIcon);
    engine.rootContext()->setContextProperty("initialHideWebHeader", hideWebHeader);
    engine.rootContext()->setContextProperty("storageDir", storageDir);
    engine.rootContext()->setContextProperty("cacheDir", cacheDir);

    engine.loadData(QByteArray(appWindowQml));
    if (engine.rootObjects().isEmpty()) {
        std::cerr << "Failed to load GoogleApp window QML" << std::endl;
        return -1;
    }

    return app.exec();
}
