#ifndef TESTWINDOW_H
#define TESTWINDOW_H

#pragma once

#include <QMainWindow>
#include <QPushButton>
#include <QSlider>
#include <QSpinBox>
#include <QCheckBox>
#include <QGroupBox>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include "LossMeterLabel.h"

class TestWindow : public QMainWindow
{
    Q_OBJECT

public:
    TestWindow(QWidget *parent = nullptr);

private slots:
    void updateValue(int value);
    void toggleGradient(bool enabled);
    void resetMeter();
    void onWarningStateChanged(bool isWarning);
    void onDangerStateChanged(bool isDanger);

private:
    QVector<LossMeterLabel*> m_lossMeters;
    QSlider *m_valueSlider;
    QSpinBox *m_valueSpinBox;
    QCheckBox *m_gradientCheckBox;
    QLabel *m_statusLabel;

    void createControls();
};

#endif // TESTWINDOW_H
