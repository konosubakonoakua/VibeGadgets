#if 0
#include "mainwindow.h"

#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    MainWindow w;
    w.show();
    return a.exec();
}

#else

#include <QApplication>
#include "TestWindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    TestWindow window;
    window.show();

    return app.exec();
}

#endif
