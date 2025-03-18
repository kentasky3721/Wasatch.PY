from wasatch import DeviceFinder

# 分光計を検出
finder = DeviceFinder()
device = finder.find_first()

if device:
    print(f"Connected to: {device.device_id}")

    # 露光時間設定 (例: 100ms)
    device.set_integration_time_ms(100)

    # レーザーON
    device.set_laser_enable(True)

    # スペクトル取得
    spectrum = device.get_line()
    print(f"Spectrum Data: {spectrum[:10]} ...")  # 最初の10点を表示

    # レーザーOFF
    device.set_laser_enable(False)

    # 分光計を閉じる
    device.close()
else:
    print("No spectrometer found")

