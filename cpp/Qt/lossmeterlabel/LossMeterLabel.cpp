#include "LossMeterLabel.h"
#include <QPainter>
#include <QPainterPath>
#include <QEasingCurve>
#include <QtMath>

LossMeterLabel::LossMeterLabel(QWidget *parent)
    : QLabel(parent)
    , m_value(0.0)
    , m_warningThreshold(5000.0)
    , m_dangerThreshold(8000.0)
    , m_minValue(0.0)
    , m_maxValue(10000.0)
    , m_alertBorderWidth(4)
    , m_alertLineStyle(Qt::DotLine)
    , m_warningLineStyle(Qt::DashLine)
    , m_alertOpacity(255)
    , m_warningOpacity(255)
    , m_showPercentage(false)
    , m_showValue(false)
    , m_normalColor(QColor(0, 255, 0))
    , m_warningColor(QColor(255, 255, 0))
    , m_dangerColor(QColor(255, 0, 0))
    , m_gradientStartColor(QColor(0, 255, 0))
    , m_gradientEndColor(QColor(255, 0, 0))
    , m_useGradient(true)
    , m_enableGradientAlerts(true)
    , m_useFillMode(false)
    , m_isAlerting(false)
    , m_isWarning(false)
    , m_alertState(0)
    , m_warningState(0)
{
    setAlignment(Qt::AlignCenter);
    setMinimumSize(2, 2);
    setMaximumSize(300, 300);

    QFont font = this->font();
    font.setPointSize(12);
    font.setBold(true);
    setFont(font);

    m_alertTimer = new QTimer(this);
    connect(m_alertTimer, &QTimer::timeout, this, [this]() {
        m_alertState = (m_alertState + 1) % 2;
        update();
    });

    m_warningTimer = new QTimer(this);
    connect(m_warningTimer, &QTimer::timeout, this, [this]() {
        m_warningState = (m_warningState + 1) % 2;
        update();
    });

    updateAppearance();
}


#if 1 // getter
double LossMeterLabel::value() const { return m_value; }
double LossMeterLabel::warningThreshold() const { return m_warningThreshold; }
double LossMeterLabel::dangerThreshold() const { return m_dangerThreshold; }
double LossMeterLabel::minValue() const { return m_minValue; }
double LossMeterLabel::maxValue() const { return m_maxValue; }
bool LossMeterLabel::useGradient() const { return m_useGradient; }
bool LossMeterLabel::enableGradientAlerts() const { return m_enableGradientAlerts; }
int LossMeterLabel::alertBorderWidth() const { return m_alertBorderWidth; }
Qt::PenStyle LossMeterLabel::alertLineStyle() const { return m_alertLineStyle; }
Qt::PenStyle LossMeterLabel::warningLineStyle() const { return m_warningLineStyle; }
int LossMeterLabel::alertOpacity() const  {  return m_alertOpacity;  }
int LossMeterLabel::warningOpacity() const  {  return m_warningOpacity;  }
bool LossMeterLabel::showPercentage() const  {  return m_showPercentage;  }
bool LossMeterLabel::showValue() const  {  return m_showValue;  }
bool LossMeterLabel::useFillMode() const { return m_useFillMode; }
#endif

#if 1 // setter
void LossMeterLabel::setValue(double value)
{
    value = qBound(m_minValue, value, m_maxValue);

    if (qFuzzyCompare(m_value, value))
        return;

    bool wasWarning = shouldWarn();
    bool wasDanger = shouldAlert();

    m_value = value;

    bool isWarning = shouldWarn();
    bool isDanger = shouldAlert();

    updateAppearance();

    if (wasWarning != isWarning) {
        emit warningStateChanged(isWarning);
    }
    if (wasDanger != isDanger) {
        emit dangerStateChanged(isDanger);
    }

    emit valueChanged(value);
}

void LossMeterLabel::setWarningThreshold(double threshold)
{
    m_warningThreshold = qBound(m_minValue, threshold, m_maxValue);
    updateAppearance();
}

void LossMeterLabel::setDangerThreshold(double threshold)
{
    m_dangerThreshold = qBound(m_minValue, threshold, m_maxValue);
    updateAppearance();
}

void LossMeterLabel::setMinValue(double min)
{
    m_minValue = min;
    m_value = qMax(m_value, m_minValue);
    m_warningThreshold = qMax(m_warningThreshold, m_minValue);
    m_dangerThreshold = qMax(m_dangerThreshold, m_minValue);
    updateAppearance();
}

void LossMeterLabel::setMaxValue(double max)
{
    m_maxValue = max;
    m_value = qMin(m_value, m_maxValue);
    m_warningThreshold = qMin(m_warningThreshold, m_maxValue);
    m_dangerThreshold = qMin(m_dangerThreshold, m_maxValue);
    updateAppearance();
}

void LossMeterLabel::setUseGradient(bool useGradient)
{
    if (m_useGradient != useGradient) {
        m_useGradient = useGradient;
        updateAppearance();
    }
}

void LossMeterLabel::setEnableGradientAlerts(bool enable)
{
    if (m_enableGradientAlerts != enable) {
        m_enableGradientAlerts = enable;
        updateAppearance();
    }
}

void LossMeterLabel::setAlertBorderWidth(int width)
{
    if (m_alertBorderWidth != width) {
        m_alertBorderWidth = qMax(1, width);
        update();
    }
}

void LossMeterLabel::setAlertLineStyle(Qt::PenStyle style)
{
    if (m_alertLineStyle != style) {
        m_alertLineStyle = style;
        update();
    }
}

void LossMeterLabel::setWarningLineStyle(Qt::PenStyle style)
{
    if (m_warningLineStyle != style) {
        m_warningLineStyle = style;
        update();
    }
}

void LossMeterLabel::setAlertOpacity(int opacity)
{
    int clampedOpacity = qBound(0, opacity, 255);
    if (m_alertOpacity != clampedOpacity) {
        m_alertOpacity = clampedOpacity;
        update();
    }
}

void LossMeterLabel::setWarningOpacity(int opacity)
{
    int clampedOpacity = qBound(0, opacity, 255);
    if (m_warningOpacity != clampedOpacity) {
        m_warningOpacity = clampedOpacity;
        update();
    }
}

void LossMeterLabel::setShowPercentage(bool show)
{
    if (m_showPercentage != show) {
        m_showPercentage = show;
        updateAppearance();
    }
}

void LossMeterLabel::setShowValue(bool show)
{
    if (m_showValue != show) {
        m_showValue = show;
        updateAppearance();
    }
}

void LossMeterLabel::setUseFillMode(bool useFill)
{
    if (m_useFillMode != useFill) {
        m_useFillMode = useFill;
        updateAppearance();
    }
}

void LossMeterLabel::setNormalColor(const QColor &color)
{
    m_normalColor = color;
    updateAppearance();
}

void LossMeterLabel::setWarningColor(const QColor &color)
{
    m_warningColor = color;
    updateAppearance();
}

void LossMeterLabel::setDangerColor(const QColor &color)
{
    m_dangerColor = color;
    updateAppearance();
}

void LossMeterLabel::setGradientColors(const QColor &start, const QColor &end)
{
    m_gradientStartColor = start;
    m_gradientEndColor = end;
    updateAppearance();
}
#endif

#if 1
bool LossMeterLabel::shouldAlert() const
{
    return m_value >= m_dangerThreshold;
}

bool LossMeterLabel::shouldWarn() const
{
    return m_value >= m_warningThreshold && m_value < m_dangerThreshold;
}

void LossMeterLabel::reset()
{
    m_value = m_minValue;
    stopAlertAnimation();
    stopWarningAnimation();
    updateAppearance();
    emit valueChanged(m_value);
}

void LossMeterLabel::updateAppearance()
{
    QColor backgroundColor;

    if (m_useGradient) {
        backgroundColor = calculateGradientColor(m_value);

        if (m_enableGradientAlerts) {
            if (shouldAlert()) {
                startAlertAnimation();
                stopWarningAnimation();
            } else if (shouldWarn()) {
                startWarningAnimation();
                stopAlertAnimation();
            } else {
                stopAlertAnimation();
                stopWarningAnimation();
            }
        } else {
            stopAlertAnimation();
            stopWarningAnimation();
        }
    } else {
        if (shouldAlert()) {
            backgroundColor = m_dangerColor;
            startAlertAnimation();
            stopWarningAnimation();
        } else if (shouldWarn()) {
            backgroundColor = m_warningColor;
            startWarningAnimation();
            stopAlertAnimation();
        } else {
            backgroundColor = m_normalColor;
            stopAlertAnimation();
            stopWarningAnimation();
        }
    }

    int radius = width() / 2;
    QString style = QString(
                        "QLabel {"
                        "   border-radius: %1px;"
                        "   background-color: %2;"
                        "   color: white;"
                        "   font-weight: bold;"
                        "   border: 2px solid #333;"
                        "}"
                        ).arg(radius).arg(backgroundColor.name());

    setStyleSheet(style);
    

    QString displayText;

    if (m_showValue && m_showPercentage) {
        double percentage = ((m_value - m_minValue) / (m_maxValue - m_minValue)) * 100.0;
        displayText = QString("%1\n%2%").arg(m_value, 0, 'f', 1).arg(percentage, 0, 'f', 1);
    } else if (m_showValue) {
        displayText = QString::number(m_value, 'f', 1);
    } else if (m_showPercentage) {
        double percentage = ((m_value - m_minValue) / (m_maxValue - m_minValue)) * 100.0;
        displayText = QString("%1%").arg(percentage, 0, 'f', 1);
    } else {
        displayText = "";
    }

    setText(displayText);
}

QColor LossMeterLabel::calculateGradientColor(double value) const
{
    double normalized = normalizeValue(value);

    int r = m_gradientStartColor.red() + normalized * (m_gradientEndColor.red() - m_gradientStartColor.red());
    int g = m_gradientStartColor.green() + normalized * (m_gradientEndColor.green() - m_gradientStartColor.green());
    int b = m_gradientStartColor.blue() + normalized * (m_gradientEndColor.blue() - m_gradientStartColor.blue());

    return QColor(r, g, b);
}

double LossMeterLabel::normalizeValue(double value) const
{
    return qBound(0.0, (value - m_minValue) / (m_maxValue - m_minValue), 1.0);
}

void LossMeterLabel::startAlertAnimation()
{
    if (!m_isAlerting) {
        m_isAlerting = true;
        m_alertTimer->start(300);
    }
}

void LossMeterLabel::stopAlertAnimation()
{
    if (m_isAlerting) {
        m_isAlerting = false;
        m_alertTimer->stop();
        m_alertState = 0;
    }
}

void LossMeterLabel::startWarningAnimation()
{
    if (!m_isWarning) {
        m_isWarning = true;
        m_warningTimer->start(600);
    }
}

void LossMeterLabel::stopWarningAnimation()
{
    if (m_isWarning) {
        m_isWarning = false;
        m_warningTimer->stop();
        m_warningState = 0;
    }
}

void LossMeterLabel::paintEvent(QPaintEvent *event)
{
    QLabel::paintEvent(event);

    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setBrush(Qt::NoBrush);

    int borderOffset = m_alertBorderWidth / 2 + 2;
    QRectF innerRect = this->rect().adjusted(borderOffset, borderOffset, -borderOffset, -borderOffset);

    if (m_isAlerting && m_alertState == 1) {
        QColor alertColor = Qt::white;
        alertColor.setAlpha(m_alertOpacity);
        
        if (m_useFillMode) {
            alertColor.setAlpha(m_alertOpacity);
            painter.setBrush(QBrush(alertColor));
            painter.setPen(Qt::NoPen);
            painter.drawEllipse(innerRect);
        } else {
            painter.setPen(QPen(alertColor, m_alertBorderWidth, m_alertLineStyle));
            painter.drawEllipse(innerRect);
        }
    }

    if (m_isWarning && m_warningState == 1) {
        QColor warningColor = Qt::white;
        warningColor.setAlpha(m_warningOpacity);
        
        if (m_useFillMode) {
            warningColor.setAlpha(m_warningOpacity);
            painter.setBrush(QBrush(warningColor));
            painter.setPen(Qt::NoPen);
            painter.drawEllipse(innerRect);
        } else {
            painter.setPen(QPen(warningColor, m_alertBorderWidth, m_warningLineStyle));
            painter.drawEllipse(innerRect);
        }
    }
}

void LossMeterLabel::resizeEvent(QResizeEvent *event)
{
    QLabel::resizeEvent(event);
    updateAppearance();
}

#endif
