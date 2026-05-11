#!/usr/bin/env python3
"""
创建带GPS信息的测试图像
"""
from PIL import Image
import piexif
import os

def create_test_photo_with_gps():
    """创建一个带有GPS EXIF信息的测试图像"""
    output_dir = "/workspace/第一次无人机数据"
    os.makedirs(output_dir, exist_ok=True)
    
    img = Image.new('RGB', (800, 600), color=(73, 109, 137))
    
    lat = 28.237419
    lon = 112.946843
    alt = 284.4
    
    def dms(value):
        abs_value = abs(value)
        degrees = int(abs_value)
        minutes_full = (abs_value - degrees) * 60
        minutes = int(minutes_full)
        seconds = int((minutes_full - minutes) * 60 * 10000)
        return (degrees, 1), (minutes, 1), (seconds, 10000)
    
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: dms(lat),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: dms(lon),
        piexif.GPSIFD.GPSAltitudeRef: 0,
        piexif.GPSIFD.GPSAltitude: (int(abs(alt) * 10000), 10000),
    }
    
    exif_dict = {"0th": {}, "Exif": {}, "GPS": gps_ifd, "1st": {}, "thumbnail": None}
    exif_bytes = piexif.dump(exif_dict)
    
    output_path = os.path.join(output_dir, "DJI_001.jpg")
    img.save(output_path, "JPEG", exif=exif_bytes)
    print(f"✅ 创建测试图像: {output_path}")
    print(f"   GPS坐标: ({lat}, {lon}, {alt})")
    
    output_path2 = os.path.join(output_dir, "DJI_002.jpg")
    lat2, lon2, alt2 = 28.238500, 112.947800, 285.2
    gps_ifd2 = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: dms(lat2),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: dms(lon2),
        piexif.GPSIFD.GPSAltitudeRef: 0,
        piexif.GPSIFD.GPSAltitude: (int(abs(alt2) * 10000), 10000),
    }
    exif_dict2 = {"0th": {}, "Exif": {}, "GPS": gps_ifd2, "1st": {}, "thumbnail": None}
    img.save(output_path2, "JPEG", exif=piexif.dump(exif_dict2))
    print(f"✅ 创建测试图像: {output_path2}")
    print(f"   GPS坐标: ({lat2}, {lon2}, {alt2})")
    
    output_path3 = os.path.join(output_dir, "DJI_003.jpg")
    lat3, lon3, alt3 = 28.236800, 112.945600, 283.8
    gps_ifd3 = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: dms(lat3),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: dms(lon3),
        piexif.GPSIFD.GPSAltitudeRef: 0,
        piexif.GPSIFD.GPSAltitude: (int(abs(alt3) * 10000), 10000),
    }
    exif_dict3 = {"0th": {}, "Exif": {}, "GPS": gps_ifd3, "1st": {}, "thumbnail": None}
    img.save(output_path3, "JPEG", exif=piexif.dump(exif_dict3))
    print(f"✅ 创建测试图像: {output_path3}")
    print(f"   GPS坐标: ({lat3}, {lon3}, {alt3})")

if __name__ == "__main__":
    create_test_photo_with_gps()
    print("\n测试图像创建完成！")
