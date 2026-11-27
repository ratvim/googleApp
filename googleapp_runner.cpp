#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QQuickWebEngineProfile>
#include <QWebEngineClientHints>
#include <QWebEngineScript>
#include <QCommandLineParser>
#include <QCommandLineOption>
#include <QIcon>
#include <QPixmap>
#include <QFile>
#include <QFileInfo>
#include <QDir>
#include <QUrl>
#include <QStandardPaths>
#include <QProcess>
#include <QMetaObject>
#include <QLocalServer>
#include <QLocalSocket>
#include <unistd.h>
#include <KF6/KWindowSystem/kwindoweffects.h>
#include <QtWebEngineQuick/qtwebenginequickglobal.h>
#include <iostream>

static QString detectWidevinePath() {
    const QStringList candidates = {
        "/var/lib/flatpak/app/com.google.Chrome/x86_64/stable/active/files/extra/WidevineCdm/_platform_specific/linux_x64/libwidevinecdm.so",
        "/opt/google/chrome/WidevineCdm/_platform_specific/linux_x64/libwidevinecdm.so",
        "/opt/google/chrome/libwidevinecdm.so",
        "/usr/lib/chromium/libwidevinecdm.so",
        "/usr/lib64/chromium/libwidevinecdm.so",
        "/usr/lib/qt6/plugins/ppapi/libwidevinecdm.so",
        QDir::homePath() + "/.local/lib/widevine/libwidevinecdm.so"
    };
    for (const QString &path : candidates) {
        if (QFile::exists(path)) {
            return path;
        }
    }
    return QString();
}

static const char *stealthScriptSource = R"JS(
(function() {
    try {
        // 1. Mask automation webdriver flag
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // 2. Mock authentic Chrome object and properties expected by Google Sign-In & BotGuard
        if (!window.chrome) {
            window.chrome = {};
        }
        window.chrome.app = {
            isInstalled: false,
            InstallState: { DISABLED: "disabled", INSTALLED: "installed", NOT_INSTALLED: "not_installed" },
            RunningState: { CANNOT_RUN: "cannot_run", READY_TO_RUN: "ready_to_run", RUNNING: "running" }
        };
        window.chrome.csi = function() {};
        window.chrome.loadTimes = function() {};
        window.chrome.runtime = {
            OnInstalledReason: { CHROME_UPDATE: "chrome_update", INSTALL: "install", SHARED_MODULE_UPDATE: "shared_module_update", UPDATE: "update" },
            OnRestartRequiredReason: { APP_UPDATE: "app_update", OS_UPDATE: "os_update", PERIODIC: "periodic" },
            PlatformArch: { ARM: "arm", ARM64: "arm64", MIPS: "mips", MIPS64: "mips64", X86_32: "x86-32", X86_64: "x86-64" },
            PlatformNaclArch: { ARM: "arm", MIPS: "mips", MIPS64: "mips64", X86_32: "x86-32", X86_64: "x86-64" },
            PlatformOs: { ANDROID: "android", CROS: "cros", LINUX: "linux", MAC: "mac", OPENBSD: "openbsd", WIN: "win" },
            RequestUpdateCheckStatus: { NO_UPDATE: "no_update", THROTTLED: "throttled", UPDATE_AVAILABLE: "update_available" }
        };

        // 3. Mock Chrome PDF Viewer & standard browser plugins
        const mockPlugins = [
            { name: "PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" },
            { name: "Chrome PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" },
            { name: "Chromium PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" },
            { name: "Microsoft Edge PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" },
            { name: "WebKit built-in PDF", filename: "internal-pdf-viewer", description: "Portable Document Format" }
        ];
        Object.defineProperty(navigator, 'plugins', {
            get: () => mockPlugins,
            configurable: true
        });
    } catch(e) {}
})();
)JS";

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
    flags: isFrameless ? (Qt.Window | Qt.FramelessWindowHint) : Qt.Window
    color: sysPalette.window

    SystemPalette {
        id: sysPalette
        colorGroup: SystemPalette.Active
    }

    property bool webHeaderHidden: initialHideWebHeader
    property bool frameless: isFrameless

    function activateWindow() {
        if (root.visibility === Window.Minimized) {
            root.showNormal()
        }
        root.show()
        root.raise()
        root.requestActivate()
    }

    // Single Application Top Bar (Custom System-styled Header with Window Controls)
    Rectangle {
        id: appHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: isFrameless ? 38 : 0
        visible: isFrameless
        color: sysPalette.window
        z: 100

        // Subtle bottom border matching system contrast
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Qt.rgba(sysPalette.windowText.r, sysPalette.windowText.g, sysPalette.windowText.b, 0.12)
        }

        DragHandler {
            enabled: isFrameless
            target: null
            onActiveChanged: if (active) root.startSystemMove()
        }

        TapHandler {
            enabled: isFrameless
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
            anchors.leftMargin: 8
            anchors.rightMargin: 0
            spacing: 6

            // Application Icon (Clickable -> Redirects to Home)
            Rectangle {
                id: appIconBtn
                Layout.preferredWidth: 30
                Layout.preferredHeight: 30
                radius: 6
                color: iconMouse.containsMouse ? Qt.rgba(sysPalette.windowText.r, sysPalette.windowText.g, sysPalette.windowText.b, 0.14) : "transparent"

                Image {
                    source: appIconUrl
                    visible: appIconUrl !== ""
                    anchors.centerIn: parent
                    width: 20
                    height: 20
                    fillMode: Image.PreserveAspectFit
                }

                MouseArea {
                    id: iconMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        webView.url = appUrl
                    }
                }

                ToolTip.visible: iconMouse.containsMouse
                ToolTip.delay: 350
                ToolTip.text: "Home (" + appName + ")"
            }

            // Application Name
            Text {
                text: appName
                color: sysPalette.windowText
                font.pixelSize: 13
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                Layout.alignment: Qt.AlignVCenter
            }

            // Draggable Spacer
            Item {
                Layout.fillWidth: true
                height: 1
            }

            // Window Action Buttons (Minimize, Maximize, Close)
            RowLayout {
                spacing: 0
                Layout.alignment: Qt.AlignRight

                // Minimize
                Rectangle {
                    Layout.preferredWidth: 46
                    Layout.preferredHeight: 38
                    color: minMouse.containsMouse ? "#2d3342" : "transparent"
                    Text {
                        text: "—"
                        color: "#c0caf5"
                        font.pixelSize: 12
                        anchors.centerIn: parent
                    }
                    MouseArea {
                        id: minMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showMinimized()
                    }
                }

                // Maximize / Restore
                Rectangle {
                    Layout.preferredWidth: 46
                    Layout.preferredHeight: 38
                    color: maxMouse.containsMouse ? "#2d3342" : "transparent"
                    Text {
                        text: root.visibility === Window.Maximized ? "❐" : "□"
                        color: "#c0caf5"
                        font.pixelSize: 12
                        anchors.centerIn: parent
                    }
                    MouseArea {
                        id: maxMouse
                        anchors.fill: parent
                        hoverEnabled: true
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
                    Layout.preferredWidth: 46
                    Layout.preferredHeight: 38
                    color: closeMouse.containsMouse ? "#e81123" : "transparent"
                    Text {
                        text: "✕"
                        color: "#ffffff"
                        font.pixelSize: 13
                        anchors.centerIn: parent
                    }
                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
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
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
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
                var target = request.requestedUrl.toString();
                // If it's an authentication or service internal flow, keep inside webView
                if (target.indexOf("accounts.google.com") !== -1 ||
                    target.indexOf("login") !== -1 ||
                    target.indexOf("auth") !== -1 ||
                    target.indexOf("signin") !== -1) {
                    request.openIn(webView);
                } else {
                    // External link: open in user's system web browser so user never loses their app window
                    Qt.openUrlExternally(request.requestedUrl);
                }
            }
        }

    // Window Edge Resize Handlers for Frameless mode
    MouseArea {
        enabled: isFrameless
        anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 6; z: 200
        cursorShape: Qt.SizeHorCursor
        onPressed: root.startSystemResize(Qt.LeftEdge)
    }
    MouseArea {
        enabled: isFrameless
        anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 6; z: 200
        cursorShape: Qt.SizeHorCursor
        onPressed: root.startSystemResize(Qt.RightEdge)
    }
    MouseArea {
        enabled: isFrameless
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; height: 6; z: 200
        cursorShape: Qt.SizeVerCursor
        onPressed: root.startSystemResize(Qt.TopEdge)
    }
    MouseArea {
        enabled: isFrameless
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; height: 6; z: 200
        cursorShape: Qt.SizeVerCursor
        onPressed: root.startSystemResize(Qt.BottomEdge)
    }
    MouseArea {
        enabled: isFrameless
        anchors.top: parent.top; anchors.left: parent.left; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeFDiagCursor
        onPressed: root.startSystemResize(Qt.TopEdge | Qt.LeftEdge)
    }
    MouseArea {
        enabled: isFrameless
        anchors.top: parent.top; anchors.right: parent.right; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeBDiagCursor
        onPressed: root.startSystemResize(Qt.TopEdge | Qt.RightEdge)
    }
    MouseArea {
        enabled: isFrameless
        anchors.bottom: parent.bottom; anchors.left: parent.left; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeBDiagCursor
        onPressed: root.startSystemResize(Qt.BottomEdge | Qt.LeftEdge)
    }
    MouseArea {
        enabled: isFrameless
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
    Shortcut { sequence: "Alt+Home"; onActivated: webView.url = appUrl }
    Shortcut { sequence: "Ctrl+H"; onActivated: { root.webHeaderHidden = !root.webHeaderHidden; webView.applyTopBarVisibility(); } }
    Shortcut { sequence: "Ctrl+O"; onActivated: Qt.openUrlExternally(webView.url) }
    Shortcut { sequence: "Ctrl+Q"; onActivated: root.close() }
}
)QML";

int main(int argc, char *argv[]) {
    QString pwStore = "detect";
    QString earlySlug = "web-app";
    QString customWidevine;
    bool framelessRequested = false;

    for (int i = 1; i < argc; ++i) {
        QString a = QString::fromUtf8(argv[i]);
        if (a.startsWith("--password-store=")) {
            pwStore = a.mid(17);
        } else if (a == "--password-store" && i + 1 < argc) {
            pwStore = QString::fromUtf8(argv[i + 1]);
        } else if (a.startsWith("--slug=")) {
            earlySlug = a.mid(7);
        } else if (a == "--slug" && i + 1 < argc) {
            earlySlug = QString::fromUtf8(argv[i + 1]);
        } else if (a.startsWith("--widevine-path=")) {
            customWidevine = a.mid(16);
        } else if (a == "--widevine-path" && i + 1 < argc) {
            customWidevine = QString::fromUtf8(argv[i + 1]);
        } else if (a == "--frameless") {
            framelessRequested = true;
        }
    }

    // Auto-detect or apply Widevine DRM module for media streaming (Hotstar, Netflix, etc.)
    QString widevinePath = !customWidevine.isEmpty() ? customWidevine : detectWidevinePath();
    QString widevineFlag = !widevinePath.isEmpty() ? QString(" --widevine-path=%1").arg(widevinePath) : QString();

    // Set Chromium flags with KWallet / KeepSecret password-store and Widevine DRM
    QString chromiumFlags = QString(
        "--no-sandbox "
        "--password-store=%1"
        "%2 "
        "--disable-blink-features=AutomationControlled "
        "--enable-features=NetworkService,NetworkServiceInProcess"
    ).arg(pwStore, widevineFlag);
    qputenv("QTWEBENGINE_CHROMIUM_FLAGS", chromiumFlags.toUtf8());

    QtWebEngineQuick::initialize();
    QGuiApplication app(argc, argv);

    // Single-instance check: If an instance is already running for this slug, activate it and exit
    QString serverName = QString("googleapp-single-%1-%2").arg(getuid()).arg(earlySlug);
    QLocalSocket probeSocket;
    probeSocket.connectToServer(serverName);
    if (probeSocket.waitForConnected(400)) {
        QByteArray activationToken = qgetenv("XDG_ACTIVATION_TOKEN");
        QString msg = QString("ACTIVATE %1\n").arg(QString::fromUtf8(activationToken));
        probeSocket.write(msg.toUtf8());
        probeSocket.waitForBytesWritten(1000);
        probeSocket.disconnectFromServer();
        std::cout << "Existing instance found for " << earlySlug.toStdString() << ", bringing window to front." << std::endl;
        return 0;
    }

    // No existing instance; setup listener
    QLocalServer::removeServer(serverName);
    QLocalServer localServer;
    if (!localServer.listen(serverName)) {
        std::cerr << "Warning: Could not start single-instance listener on "
                  << serverName.toStdString() << ": "
                  << localServer.errorString().toStdString() << std::endl;
    }

    QCommandLineParser parser;
    parser.setApplicationDescription("GoogleApp Standalone Web App Runner");
    parser.addHelpOption();

    QCommandLineOption slugOpt("slug", "Application slug identifier", "slug", "web-app");
    QCommandLineOption nameOpt("name", "Application display name", "name", "Web App");
    QCommandLineOption urlOpt("url", "Application web URL", "url", "https://google.com");
    QCommandLineOption iconOpt("icon", "Application icon file or name", "icon", "");
    QCommandLineOption profileDirOpt("profile-dir", "Custom persistent profile directory path", "path", "");
    QCommandLineOption uaOpt("user-agent", "Custom HTTP User-Agent string", "ua", "");
    QCommandLineOption pwStoreOpt("password-store", "Password and token keyring backend (detect, kwallet6, gnome-libsecret, basic)", "store", "detect");
    QCommandLineOption widevineOpt("widevine-path", "Path to libwidevinecdm.so DRM module", "path", "");
    QCommandLineOption nativeFrameOpt("native-frame", "Use native system window decorations instead of custom top bar");
    QCommandLineOption framelessOpt("frameless", "Use custom frameless top bar (default)");
    QCommandLineOption showHeaderOpt("show-web-header", "Keep the web UI top bar visible by default");

    parser.addOption(slugOpt);
    parser.addOption(nameOpt);
    parser.addOption(urlOpt);
    parser.addOption(iconOpt);
    parser.addOption(profileDirOpt);
    parser.addOption(uaOpt);
    parser.addOption(pwStoreOpt);
    parser.addOption(widevineOpt);
    parser.addOption(nativeFrameOpt);
    parser.addOption(framelessOpt);
    parser.addOption(showHeaderOpt);

    parser.process(app);

    QString slug = parser.value(slugOpt);
    QString name = parser.value(nameOpt);
    QString url = parser.value(urlOpt);
    QString icon = parser.value(iconOpt);
    bool isFrameless = !parser.isSet(nativeFrameOpt);
    bool hideWebHeader = !parser.isSet(showHeaderOpt);

    QString desktopId = QString("googleapp-%1").arg(slug);
    app.setDesktopFileName(desktopId);
    app.setApplicationName(name);

    // Standardized persistent profile & cache directories
    QString storageDir = parser.value(profileDirOpt);
    if (storageDir.isEmpty()) {
        storageDir = QString("%1/.local/share/googleapp-profiles/%2").arg(QDir::homePath(), desktopId);
    }
    QString cacheDir = QString("%1/.cache/googleapp/%2").arg(QDir::homePath(), desktopId);

    QDir().mkpath(storageDir);
    QDir().mkpath(cacheDir);

    // Thorough Icon Resolution (File path, Theme Icon, or Cached Pixmap)
    QString resolvedIconPath;
    QIcon winIcon;
    if (!icon.isEmpty()) {
        if (QFile::exists(icon)) {
            resolvedIconPath = QFileInfo(icon).absoluteFilePath();
            winIcon = QIcon(resolvedIconPath);
        } else {
            winIcon = QIcon::fromTheme(icon);
            QProcess proc;
            proc.start("kiconfinder6", QStringList() << icon);
            if (proc.waitForFinished(600) && proc.exitCode() == 0) {
                QString out = QString::fromUtf8(proc.readAllStandardOutput()).trimmed();
                if (!out.isEmpty() && QFile::exists(out)) {
                    resolvedIconPath = out;
                }
            }
        }
    }

    if (resolvedIconPath.isEmpty() && !icon.isEmpty()) {
        QString home = QDir::homePath();
        const QStringList exts = {"png", "svg", "ico", "jpg", "jpeg", "webp"};
        for (const QString &ext : exts) {
            QString p1 = QString("%1/.local/share/icons/hicolor/128x128/apps/%2.%3").arg(home, icon, ext);
            if (QFile::exists(p1)) {
                resolvedIconPath = p1;
                winIcon = QIcon(p1);
                break;
            }
            QString p2 = QString("%1/.local/share/icons/hicolor/scalable/apps/%2.%3").arg(home, icon, ext);
            if (QFile::exists(p2)) {
                resolvedIconPath = p2;
                winIcon = QIcon(p2);
                break;
            }
        }
    }

    if (resolvedIconPath.isEmpty() && !winIcon.isNull()) {
        QString cachedPng = QString("%1/app_icon.png").arg(cacheDir);
        QPixmap pix = winIcon.pixmap(128, 128);
        if (!pix.isNull()) {
            pix.save(cachedPng, "PNG");
            resolvedIconPath = cachedPng;
        }
    }

    if (!winIcon.isNull()) {
        app.setWindowIcon(winIcon);
    }

    QString appIconUrl = !resolvedIconPath.isEmpty() ? QUrl::fromLocalFile(resolvedIconPath).toString() : "";

    // Explicitly configure disk-backed persistent profile in C++
    QQuickWebEngineProfile profile;
    profile.setStorageName(slug);
    profile.setPersistentStoragePath(storageDir);
    profile.setCachePath(cacheDir);
    profile.setOffTheRecord(false);
    profile.setPersistentCookiesPolicy(QQuickWebEngineProfile::AllowPersistentCookies);
    profile.setPersistentPermissionsPolicy(QQuickWebEngineProfile::PersistentPermissionsPolicy::StoreOnDisk);
    profile.setHttpCacheType(QQuickWebEngineProfile::DiskHttpCache);

    // Chrome 140 User-Agent matching underlying Chromium 140.0.7339.264 engine
    QString userAgent = parser.value(uaOpt);
    if (userAgent.isEmpty()) {
        userAgent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";
    }
    profile.setHttpUserAgent(userAgent);

    // Set Chrome Client Hints (Sec-CH-UA) to match authentic Google Chrome 140
    if (auto hints = profile.clientHints()) {
        QVariantMap brands;
        brands.insert("Google Chrome", "140.0.7339.264");
        brands.insert("Chromium", "140.0.7339.264");
        brands.insert("Not=A?Brand", "24.0.0.0");
        hints->setFullVersionList(brands);
        hints->setFullVersion("140.0.7339.264");
        hints->setPlatform("Linux");
        hints->setArch("x86");
        hints->setBitness("64");
        hints->setIsMobile(false);
    }

    // Inject stealth script into main world at DocumentCreation to satisfy Google Sign-In checks
    QWebEngineScript stealthScript;
    stealthScript.setName("stealth_script");
    stealthScript.setSourceCode(stealthScriptSource);
    stealthScript.setInjectionPoint(QWebEngineScript::DocumentCreation);
    stealthScript.setWorldId(QWebEngineScript::MainWorld);
    stealthScript.setRunsOnSubFrames(true);

    QObject *scriptsCollection = profile.property("userScripts").value<QObject*>();
    if (scriptsCollection) {
        QMetaObject::invokeMethod(scriptsCollection, "insert", Q_ARG(QWebEngineScript, stealthScript));
    }

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("webProfile", &profile);
    engine.rootContext()->setContextProperty("appSlug", slug);
    engine.rootContext()->setContextProperty("appName", name);
    engine.rootContext()->setContextProperty("appUrl", url);
    engine.rootContext()->setContextProperty("appIconUrl", appIconUrl);
    engine.rootContext()->setContextProperty("isFrameless", isFrameless);
    engine.rootContext()->setContextProperty("initialHideWebHeader", hideWebHeader);
    engine.rootContext()->setContextProperty("storageDir", storageDir);
    engine.rootContext()->setContextProperty("cacheDir", cacheDir);

    // Handle single-instance activation signals when launcher is clicked again
    QObject::connect(&localServer, &QLocalServer::newConnection, [&]() {
        QLocalSocket *client = localServer.nextPendingConnection();
        if (!client) return;
        QObject::connect(client, &QLocalSocket::readyRead, [client, &engine]() {
            QByteArray line = client->readLine().trimmed();
            QString token;
            if (line.startsWith("ACTIVATE")) {
                token = QString::fromUtf8(line.mid(8)).trimmed();
            }
            if (!token.isEmpty()) {
                qputenv("XDG_ACTIVATION_TOKEN", token.toUtf8());
            }

            const auto roots = engine.rootObjects();
            if (!roots.isEmpty()) {
                QMetaObject::invokeMethod(roots.first(), "activateWindow");
                if (auto win = qobject_cast<QQuickWindow*>(roots.first())) {
                    if (win->visibility() == QWindow::Minimized) {
                        win->showNormal();
                    }
                    win->show();
                    win->raise();
                    win->requestActivate();
                }
            }
            client->disconnectFromServer();
            client->deleteLater();
        });
    });

    engine.loadData(QByteArray(appWindowQml));
    if (engine.rootObjects().isEmpty()) {
        std::cerr << "Failed to load GoogleApp window QML" << std::endl;
        return -1;
    }

    // Apply native KDE KWin blur and contrast effects if available
    if (auto win = qobject_cast<QQuickWindow*>(engine.rootObjects().first())) {
        if (!winIcon.isNull()) {
            win->setIcon(winIcon);
        }
        KWindowEffects::enableBlurBehind(win, true);
        KWindowEffects::enableBackgroundContrast(win, true);
    }

    return app.exec();
}
