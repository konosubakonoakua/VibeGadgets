#ifndef LOSSMETERLABEL_H
#define LOSSMETERLABEL_H

#pragma once

#include <QLabel>
#include <QTimer>
#include <QLinearGradient>
#include <QPropertyAnimation>

class LossMeterLabel : public QLabel
{
    Q_OBJECT
    Q_PROPERTY(double value READ value WRITE setValue NOTIFY valueChanged)
    Q_PROPERTY(double warningThreshold READ warningThreshold WRITE setWarningThreshold)
    Q_PROPERTY(double dangerThreshold READ dangerThreshold WRITE setDangerThreshold)
    Q_PROPERTY(double minValue READ minValue WRITE setMinValue)
    Q_PROPERTY(double maxValue READ maxValue WRITE setMaxValue)
    Q_PROPERTY(bool useGradient READ useGradient WRITE setUseGradient)
    Q_PROPERTY(bool enableGradientAlerts READ enableGradientAlerts WRITE setEnableGradientAlerts)
    Q_PROPERTY(int alertBorderWidth READ alertBorderWidth WRITE setAlertBorderWidth)
    Q_PROPERTY(Qt::PenStyle alertLineStyle READ alertLineStyle WRITE setAlertLineStyle)
    Q_PROPERTY(Qt::PenStyle warningLineStyle READ warningLineStyle WRITE setWarningLineStyle)
    Q_PROPERTY(int alertOpacity READ alertOpacity WRITE setAlertOpacity)
    Q_PROPERTY(int warningOpacity READ warningOpacity WRITE setWarningOpacity)
    Q_PROPERTY(bool showPercentage READ showPercentage WRITE setShowPercentage)
    Q_PROPERTY(bool showValue READ showValue WRITE setShowValue)


public:
    explicit LossMeterLabel(QWidget *parent = nullptr);

    // Getter methods
    double value() const;
    double warningThreshold() const;
    double dangerThreshold() const;
    double minValue() const;
    double maxValue() const;
    bool useGradient() const;
    bool enableGradientAlerts() const;
    int alertBorderWidth() const;
    Qt::PenStyle alertLineStyle() const;
    Qt::PenStyle warningLineStyle() const;
    int alertOpacity() const;
    int warningOpacity() const;
    bool showPercentage() const;
    bool showValue() const;

    // Color settings
    void setNormalColor(const QColor &color);
    void setWarningColor(const QColor &color);
    void setDangerColor(const QColor &color);
    void setGradientColors(const QColor &start, const QColor &end);

public slots:
    void setValue(double value);
    void setWarningThreshold(double threshold);
    void setDangerThreshold(double threshold);
    void setMinValue(double min);
    void setMaxValue(double max);
    void setUseGradient(bool useGradient);
    void setEnableGradientAlerts(bool enable);
    void setAlertBorderWidth(int width);
    void setAlertLineStyle(Qt::PenStyle style);
    void setWarningLineStyle(Qt::PenStyle style);
    void setAlertOpacity(int opacity);
    void setWarningOpacity(int opacity);
    void setShowPercentage(bool show);
    void setShowValue(bool show);
    void reset();

signals:
    void valueChanged(double value);
    void warningStateChanged(bool isWarning);
    void dangerStateChanged(bool isDanger);

protected:
    void paintEvent(QPaintEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;

private:
    void updateAppearance();
    void startAlertAnimation();
    void stopAlertAnimation();
    void startWarningAnimation();
    void stopWarningAnimation();
    QColor calculateGradientColor(double value) const;
    double normalizeValue(double value) const;
    bool shouldAlert() const;
    bool shouldWarn() const;

    double m_value;
    double m_warningThreshold;
    double m_dangerThreshold;
    double m_minValue;
    double m_maxValue;
    int m_alertBorderWidth;
    Qt::PenStyle m_alertLineStyle;
    Qt::PenStyle m_warningLineStyle;
    int m_alertOpacity;
    int m_warningOpacity;
    bool m_showPercentage;
    bool m_showValue;

    QColor m_normalColor;
    QColor m_warningColor;
    QColor m_dangerColor;
    QColor m_gradientStartColor;
    QColor m_gradientEndColor;

    bool m_useGradient;
    bool m_enableGradientAlerts;
    bool m_isAlerting;
    bool m_isWarning;
    int m_alertState;
    int m_warningState;
    QTimer *m_alertTimer;
    QTimer *m_warningTimer;
};

#endif // LOSSMETERLABLE_H
