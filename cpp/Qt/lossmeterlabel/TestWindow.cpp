#include "TestWindow.h"
#include <QApplication>
#include <QStyle>
#include <QComboBox>
#include <QGridLayout>

TestWindow::TestWindow(QWidget *parent)
    : QMainWindow(parent)
{
    setWindowTitle("LossMeterLabel Test");
    setMinimumSize(1000, 800);

    QWidget *centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);

    QHBoxLayout *mainLayout = new QHBoxLayout(centralWidget);

    // Left side: Multiple meter displays
    QGroupBox *metersGroup = new QGroupBox("Meter Displays", this);
    QGridLayout *metersLayout = new QGridLayout(metersGroup);

    // Create multiple meters with different sizes
    QList<int> sizes = {10, 15, 20, 25, 30, 35, 40, 45, 50, 100, 150, 200};
    m_lossMeters.resize(sizes.size());

    for (int i = 0; i < sizes.size(); ++i) {
        m_lossMeters[i] = new LossMeterLabel(this);
        m_lossMeters[i]->setFixedSize(sizes[i], sizes[i]);
        m_lossMeters[i]->setMinValue(0);
        m_lossMeters[i]->setMaxValue(10000);
        m_lossMeters[i]->setWarningThreshold(5000);
        m_lossMeters[i]->setDangerThreshold(8000);

        // Connect signals from the first meter to status updates
        if (i == 0) {
            connect(m_lossMeters[i], &LossMeterLabel::warningStateChanged, this, &TestWindow::onWarningStateChanged);
            connect(m_lossMeters[i], &LossMeterLabel::dangerStateChanged, this, &TestWindow::onDangerStateChanged);
        }

        metersLayout->addWidget(m_lossMeters[i], i / 2, i % 2, Qt::AlignCenter);
    }

    m_statusLabel = new QLabel("Status: Normal", this);
    m_statusLabel->setAlignment(Qt::AlignCenter);
    QFont statusFont = m_statusLabel->font();
    statusFont.setPointSize(14);
    statusFont.setBold(true);
    m_statusLabel->setFont(statusFont);
    metersLayout->addWidget(m_statusLabel, sizes.size() / 2, 0, 1, 2);

    // Right side: Control panel
    QGroupBox *controlGroup = new QGroupBox("Control Panel", this);
    QVBoxLayout *controlLayout = new QVBoxLayout(controlGroup);

#if 1 // Value control group
    QGroupBox *valueGroup = new QGroupBox("Value Control", this);
    QVBoxLayout *valueGroupLayout = new QVBoxLayout(valueGroup);

    QHBoxLayout *valueLayout = new QHBoxLayout();
    valueLayout->addWidget(new QLabel("Value:", this));

    m_valueSlider = new QSlider(Qt::Horizontal, this);
    m_valueSlider->setRange(0, 10000);
    m_valueSlider->setValue(0);
    connect(m_valueSlider, &QSlider::valueChanged, this, &TestWindow::updateValue);

    m_valueSpinBox = new QSpinBox(this);
    m_valueSpinBox->setRange(0, 10000);
    m_valueSpinBox->setValue(0);
    connect(m_valueSpinBox, QOverload<int>::of(&QSpinBox::valueChanged), m_valueSlider, &QSlider::setValue);
    connect(m_valueSlider, &QSlider::valueChanged, m_valueSpinBox, &QSpinBox::setValue);
    connect(m_valueSlider, &QSlider::valueChanged, this, &TestWindow::updateValue);

    valueLayout->addWidget(m_valueSlider);
    valueLayout->addWidget(m_valueSpinBox);
    valueGroupLayout->addLayout(valueLayout);

    controlLayout->addWidget(valueGroup);
#endif

#if 1 // Display settings group
    QGroupBox *displayGroup = new QGroupBox("Display Settings", this);
    QVBoxLayout *displayLayout = new QVBoxLayout(displayGroup);

    QCheckBox *valueCheckBox = new QCheckBox("Show Value", this);
    valueCheckBox->setChecked(false);
    connect(valueCheckBox, &QCheckBox::toggled, this, [this](bool checked) {
        for (auto meter : m_lossMeters) {
            meter->setShowValue(checked);
        }
    });
    displayLayout->addWidget(valueCheckBox);

    QCheckBox *percentageCheckBox = new QCheckBox("Show Percentage", this);
    percentageCheckBox->setChecked(false);
    connect(percentageCheckBox, &QCheckBox::toggled, this, [this](bool checked) {
        for (auto meter : m_lossMeters) {
            meter->setShowPercentage(checked);
        }
    });
    displayLayout->addWidget(percentageCheckBox);

    m_gradientCheckBox = new QCheckBox("Enable Gradient Mode", this);
    m_gradientCheckBox->setChecked(true);
    connect(m_gradientCheckBox, &QCheckBox::toggled, this, &TestWindow::toggleGradient);
    displayLayout->addWidget(m_gradientCheckBox);
    
    QCheckBox *fillModeCheckBox = new QCheckBox("Enable Fill Mode", this);
    connect(fillModeCheckBox, &QCheckBox::toggled, this, [this](bool checked) {
        for (auto meter : m_lossMeters) {
            meter->setUseFillMode(checked);
        }
    });
    displayLayout->addWidget(fillModeCheckBox);
    
    QCheckBox *gradientAlertCheckBox = new QCheckBox("Enable Gradient Alerts", this);
    gradientAlertCheckBox->setChecked(true);
    connect(gradientAlertCheckBox, &QCheckBox::toggled, this, [this](bool checked) {
        for (auto meter : m_lossMeters) {
            meter->setEnableGradientAlerts(checked);
        }
    });
    displayLayout->addWidget(gradientAlertCheckBox);

    controlLayout->addWidget(displayGroup);
#endif

#if 1 // Threshold settings group
    QGroupBox *thresholdGroup = new QGroupBox("Threshold Settings", this);
    QVBoxLayout *thresholdLayout = new QVBoxLayout(thresholdGroup);

    QHBoxLayout *warningLayout = new QHBoxLayout();
    warningLayout->addWidget(new QLabel("Warning Threshold:", this));
    QSpinBox *warningSpinBox = new QSpinBox(this);
    warningSpinBox->setRange(0, 100);
    warningSpinBox->setValue(40);
    connect(warningSpinBox, QOverload<int>::of(&QSpinBox::valueChanged), this, [this](int value) {
        for (auto meter : m_lossMeters) {
            meter->setWarningThreshold(value);
        }
    });
    warningLayout->addWidget(warningSpinBox);
    thresholdLayout->addLayout(warningLayout);

    QHBoxLayout *dangerLayout = new QHBoxLayout();
    dangerLayout->addWidget(new QLabel("Danger Threshold:", this));
    QSpinBox *dangerSpinBox = new QSpinBox(this);
    dangerSpinBox->setRange(0, 100);
    dangerSpinBox->setValue(70);
    connect(dangerSpinBox, QOverload<int>::of(&QSpinBox::valueChanged), this, [this](int value) {
        for (auto meter : m_lossMeters) {
            meter->setDangerThreshold(value);
        }
    });
    dangerLayout->addWidget(dangerSpinBox);
    thresholdLayout->addLayout(dangerLayout);

    controlLayout->addWidget(thresholdGroup);
#endif

#if 1 // Alert settings group
    QGroupBox *alertGroup = new QGroupBox("Alert Settings", this);
    QVBoxLayout *alertLayout = new QVBoxLayout(alertGroup);

    // Line style settings
    QGroupBox *lineStyleGroup = new QGroupBox("Line Style", this);
    QVBoxLayout *lineStyleLayout = new QVBoxLayout(lineStyleGroup);

    QHBoxLayout *alertStyleLayout = new QHBoxLayout();
    alertStyleLayout->addWidget(new QLabel("Alert Style:", this));
    QComboBox *alertStyleCombo = new QComboBox(this);
    alertStyleCombo->addItem("Solid", QVariant::fromValue(Qt::SolidLine));
    alertStyleCombo->addItem("Dash", QVariant::fromValue(Qt::DashLine));
    alertStyleCombo->addItem("Dot", QVariant::fromValue(Qt::DotLine));
    alertStyleCombo->addItem("Dash Dot", QVariant::fromValue(Qt::DashDotLine));
    alertStyleCombo->addItem("Dash Dot Dot", QVariant::fromValue(Qt::DashDotDotLine));
    alertStyleCombo->setCurrentIndex(2);
    connect(alertStyleCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this, [this, alertStyleCombo](int index) {
        Qt::PenStyle style = static_cast<Qt::PenStyle>(alertStyleCombo->currentData().toInt());
        for (auto meter : m_lossMeters) {
            meter->setAlertLineStyle(style);
        }
    });
    alertStyleLayout->addWidget(alertStyleCombo);
    lineStyleLayout->addLayout(alertStyleLayout);

    QHBoxLayout *warningStyleLayout = new QHBoxLayout();
    warningStyleLayout->addWidget(new QLabel("Warning Style:", this));
    QComboBox *warningStyleCombo = new QComboBox(this);
    warningStyleCombo->addItem("Solid", QVariant::fromValue(Qt::SolidLine));
    warningStyleCombo->addItem("Dash", QVariant::fromValue(Qt::DashLine));
    warningStyleCombo->addItem("Dot", QVariant::fromValue(Qt::DotLine));
    warningStyleCombo->addItem("Dash Dot", QVariant::fromValue(Qt::DashDotLine));
    warningStyleCombo->addItem("Dash Dot Dot", QVariant::fromValue(Qt::DashDotDotLine));
    warningStyleCombo->setCurrentIndex(1);
    connect(warningStyleCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this, [this, warningStyleCombo](int index) {
        Qt::PenStyle style = static_cast<Qt::PenStyle>(warningStyleCombo->currentData().toInt());
        for (auto meter : m_lossMeters) {
            meter->setWarningLineStyle(style);
        }
    });
    warningStyleLayout->addWidget(warningStyleCombo);
    lineStyleLayout->addLayout(warningStyleLayout);

    alertLayout->addWidget(lineStyleGroup);

    // Opacity settings
    QGroupBox *opacityGroup = new QGroupBox("Opacity", this);
    QVBoxLayout *opacityLayout = new QVBoxLayout(opacityGroup);

    QHBoxLayout *alertOpacityLayout = new QHBoxLayout();
    alertOpacityLayout->addWidget(new QLabel("Alert Opacity:", this));
    QSlider *alertOpacitySlider = new QSlider(Qt::Horizontal, this);
    alertOpacitySlider->setRange(0, 255);
    alertOpacitySlider->setValue(255);
    connect(alertOpacitySlider, &QSlider::valueChanged, this, [this](int value) {
        for (auto meter : m_lossMeters) {
            meter->setAlertOpacity(value);
        }
    });
    alertOpacityLayout->addWidget(alertOpacitySlider);
    QLabel *alertOpacityValue = new QLabel("255", this);
    connect(alertOpacitySlider, &QSlider::valueChanged, this, [alertOpacityValue](int value) {
        alertOpacityValue->setText(QString::number(value));
    });
    alertOpacityLayout->addWidget(alertOpacityValue);
    opacityLayout->addLayout(alertOpacityLayout);

    QHBoxLayout *warningOpacityLayout = new QHBoxLayout();
    warningOpacityLayout->addWidget(new QLabel("Warning Opacity:", this));
    QSlider *warningOpacitySlider = new QSlider(Qt::Horizontal, this);
    warningOpacitySlider->setRange(0, 255);
    warningOpacitySlider->setValue(255);
    connect(warningOpacitySlider, &QSlider::valueChanged, this, [this](int value) {
        for (auto meter : m_lossMeters) {
            meter->setWarningOpacity(value);
        }
    });
    warningOpacityLayout->addWidget(warningOpacitySlider);
    QLabel *warningOpacityValue = new QLabel("255", this);
    connect(warningOpacitySlider, &QSlider::valueChanged, this, [warningOpacityValue](int value) {
        warningOpacityValue->setText(QString::number(value));
    });
    warningOpacityLayout->addWidget(warningOpacityValue);
    opacityLayout->addLayout(warningOpacityLayout);

    alertLayout->addWidget(opacityGroup);

    controlLayout->addWidget(alertGroup);
#endif

#if 1 // Control buttons
    QPushButton *resetButton = new QPushButton("Reset All", this);
    connect(resetButton, &QPushButton::clicked, this, &TestWindow::resetMeter);
    controlLayout->addWidget(resetButton);
#endif

    controlLayout->addStretch();

    mainLayout->addWidget(metersGroup, 2);
    mainLayout->addWidget(controlGroup, 1);
}

void TestWindow::updateValue(int value)
{
    for (auto meter : m_lossMeters) {
        meter->setValue(value);
    }
}

void TestWindow::toggleGradient(bool enabled)
{
    for (auto meter : m_lossMeters) {
        meter->setUseGradient(enabled);
        if (enabled) {
            meter->setGradientColors(Qt::green, Qt::red);
        }
    }
}

void TestWindow::resetMeter()
{
    m_valueSlider->setValue(0);
    for (auto meter : m_lossMeters) {
        meter->reset();
    }
}

void TestWindow::onWarningStateChanged(bool isWarning)
{
    if (isWarning) {
        m_statusLabel->setText("Status: ⚠️ Warning ⚠️");
        m_statusLabel->setStyleSheet("color: orange;");
    } else {
        m_statusLabel->setText("Status: Normal");
        m_statusLabel->setStyleSheet("color: green;");
    }
}

void TestWindow::onDangerStateChanged(bool isDanger)
{
    if (isDanger) {
        m_statusLabel->setText("Status: 🚨 Danger 🚨！");
        m_statusLabel->setStyleSheet("color: red; font-weight: bold;");
    } else {
        onWarningStateChanged(m_lossMeters[0]->value() >= m_lossMeters[0]->warningThreshold());
    }
}
