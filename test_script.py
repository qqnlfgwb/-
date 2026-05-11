#!/usr/bin/env python3
"""
测试脚本：验证UAV Exif Tool的核心功能
"""
import sys
import os
import struct
import re

GPS_INFO_TAG = 0x8825
PHOTO_READ_SIZE = 65536
JPG_EXTENSIONS = (".jpg", ".jpeg")
APP1_XMP_MARKER = b"http://ns.adobe.com/"

XMP_TAG_PATTERN = re.compile(
    r'(FlightYawDegree|FlightPitchDegree|FlightRollDegree|GimbalYawDegree|GimbalPitchDegree|GimbalRollDegree)="([^"]*)"'
)
XMP_INDEX_MAP = {
    "FlightYawDegree": 0,
    "FlightPitchDegree": 1,
    "FlightRollDegree": 2,
    "GimbalYawDegree": 3,
    "GimbalPitchDegree": 4,
    "GimbalRollDegree": 5,
}

NUMERIC_FIELD_NAMES = [
    "无人机偏航角", "无人机俯仰角", "无人机翻滚角",
    "云台偏航角", "云台俯仰角", "云台翻滚角",
    "GPS纬度", "GPS经度", "GPS高度"
]

class TestUAVExifTool:
    @staticmethod
    def _read_exif_binary_fast(file_path):
        result = [0.0] * len(NUMERIC_FIELD_NAMES)
        with open(file_path, "rb") as f:
            data = f.read(PHOTO_READ_SIZE)
        
        if len(data) < 2 or data[:2] != b"\xff\xd8":
            return TestUAVExifTool._result_list_to_dict(result)
        
        offset = 2
        while offset + 4 <= len(data):
            if data[offset] != 0xFF:
                break
            length = (data[offset + 2] << 8) | data[offset + 3]
            if length < 2:
                break
            next_offset = offset + 2 + length
            if next_offset > len(data):
                break
            
            if data[offset + 1] == 0xE1:
                app1_data = data[offset + 4:next_offset]
                if app1_data[:6] == b"Exif\x00\x00":
                    TestUAVExifTool._parse_exif_data(app1_data[6:], result)
                if APP1_XMP_MARKER in app1_data:
                    TestUAVExifTool._parse_xmp_fast(app1_data.decode("utf-8", errors="ignore"), result)
            offset = next_offset
        return TestUAVExifTool._result_list_to_dict(result)
    
    @staticmethod
    def _parse_exif_data(exif_data, result):
        if len(exif_data) < 10:
            return
        byte_order = exif_data[:2]
        if byte_order not in (b"II", b"MM"):
            return
        fmt = "<" if byte_order == b"II" else ">"
        if struct.unpack_from(fmt + "H", exif_data, 2)[0] != 0x002A:
            return
        TestUAVExifTool._find_gps_info(exif_data, struct.unpack_from(fmt + "L", exif_data, 4)[0], fmt, result)
    
    @staticmethod
    def _find_gps_info(exif_data, offset, fmt, result):
        if offset < 0 or offset + 2 > len(exif_data):
            return
        num_tags = struct.unpack_from(fmt + "H", exif_data, offset)[0]
        entry_base = offset + 2
        for tag_index in range(num_tags):
            tag_offset = entry_base + tag_index * 12
            if tag_offset + 12 > len(exif_data):
                return
            if struct.unpack_from(fmt + "H", exif_data, tag_offset)[0] == GPS_INFO_TAG:
                gps_offset = struct.unpack_from(fmt + "L", exif_data, tag_offset + 8)[0]
                TestUAVExifTool._parse_gps_info(exif_data, gps_offset, fmt, result)
                return
    
    @staticmethod
    def _parse_gps_info(exif_data, offset, fmt, result):
        if offset < 0 or offset + 2 > len(exif_data):
            return
        num_tags = struct.unpack_from(fmt + "H", exif_data, offset)[0]
        entry_base = offset + 2
        gps_values = {}
        
        for tag_index in range(num_tags):
            tag_offset = entry_base + tag_index * 12
            if tag_offset + 12 > len(exif_data):
                break
            tag_id, _, count = struct.unpack_from(fmt + "HHL", exif_data, tag_offset)
            value_offset = struct.unpack_from(fmt + "L", exif_data, tag_offset + 8)[0]
            inline_value = exif_data[tag_offset + 8:tag_offset + 12]
            
            if tag_id in (1, 3):
                gps_values[tag_id] = inline_value[:count].decode("ascii", errors="ignore").strip("\x00 ") or ("N" if tag_id == 1 else "E")
            elif tag_id in (2, 4):
                gps_values[tag_id] = TestUAVExifTool._parse_gps_coordinate(exif_data, value_offset, fmt)
            elif tag_id == 6:
                gps_values[tag_id] = TestUAVExifTool._parse_gps_altitude(exif_data, value_offset, fmt)
        
        lat, lon, alt = gps_values.get(2), gps_values.get(4), gps_values.get(6)
        lat_ref, lon_ref = gps_values.get(1, "N"), gps_values.get(3, "E")
        if lat is not None and lon is not None:
            result[6] = round(-lat if lat_ref == "S" else lat, 9)
            result[7] = round(-lon if lon_ref == "W" else lon, 9)
        if alt is not None:
            result[8] = round(alt, 9)
    
    @staticmethod
    def _parse_gps_coordinate(exif_data, offset, fmt):
        if offset < 0 or offset + 24 > len(exif_data):
            return 0.0
        deg_num, deg_den, min_num, min_den, sec_num, sec_den = struct.unpack_from(fmt + "LLLLLL", exif_data, offset)
        return (
            (deg_num / deg_den if deg_den else 0.0)
            + (min_num / min_den / 60 if min_den else 0.0)
            + (sec_num / sec_den / 3600 if sec_den else 0.0)
        )
    
    @staticmethod
    def _parse_gps_altitude(exif_data, offset, fmt):
        if offset < 0 or offset + 8 > len(exif_data):
            return 0.0
        alt_num, alt_den = struct.unpack_from(fmt + "LL", exif_data, offset)
        return alt_num / alt_den if alt_den else 0.0
    
    @staticmethod
    def _parse_xmp_fast(xmp_segment, result):
        for tag_name, tag_value in XMP_TAG_PATTERN.findall(xmp_segment):
            if tag_name in XMP_INDEX_MAP:
                result[XMP_INDEX_MAP[tag_name]] = round(float(tag_value), 9)
    
    @staticmethod
    def _result_list_to_dict(result, file_name=""):
        row = {"文件名": file_name}
        row.update(zip(NUMERIC_FIELD_NAMES, result))
        return row
    
    def test_file(self, file_path):
        print(f"\n测试文件: {file_path}")
        print("-" * 60)
        
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return None
        
        if not file_path.lower().endswith(JPG_EXTENSIONS):
            print(f"⚠️  跳过非JPG文件: {file_path}")
            return None
        
        try:
            result = self._read_exif_binary_fast(file_path)
            print("✅ EXIF解析成功!")
            print(f"文件名: {result['文件名']}")
            print(f"无人机偏航角: {result['无人机偏航角']}")
            print(f"无人机俯仰角: {result['无人机俯仰角']}")
            print(f"无人机翻滚角: {result['无人机翻滚角']}")
            print(f"云台偏航角: {result['云台偏航角']}")
            print(f"云台俯仰角: {result['云台俯仰角']}")
            print(f"云台翻滚角: {result['云台翻滚角']}")
            print(f"GPS纬度: {result['GPS纬度']}")
            print(f"GPS经度: {result['GPS经度']}")
            print(f"GPS高度: {result['GPS高度']}")
            
            if result['GPS纬度'] != 0 or result['GPS经度'] != 0:
                print(f"📍 有效GPS坐标: ({result['GPS纬度']}, {result['GPS经度']}, {result['GPS高度']})")
            else:
                print("⚠️  无有效GPS数据")
            
            return result
        except Exception as e:
            print(f"❌ 解析失败: {str(e)}")
            return None

def main():
    print("=" * 60)
    print("UAV Exif Tool - 功能测试")
    print("=" * 60)
    
    tester = TestUAVExifTool()
    
    test_dir = os.path.join(os.path.dirname(__file__), "第一次无人机数据")
    
    if not os.path.exists(test_dir):
        print(f"\n⚠️  测试目录不存在: {test_dir}")
        print("将创建一个示例测试图像来验证功能...")
        
        try:
            from PIL import Image
            import numpy as np
            
            sample_path = os.path.join(os.path.dirname(__file__), "test_sample.jpg")
            img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(sample_path)
            print(f"已创建示例图像: {sample_path}")
            tester.test_file(sample_path)
            
        except Exception as e:
            print(f"❌ 无法创建测试图像: {str(e)}")
            return
    
    photo_items = []
    if os.path.exists(test_dir):
        photo_items = sorted([
            entry.name for entry in os.scandir(test_dir)
            if entry.is_file() and entry.name.lower().endswith(JPG_EXTENSIONS)
        ])
    
    if photo_items:
        print(f"\n在测试目录中找到 {len(photo_items)} 张照片:")
        print("-" * 60)
        
        results = []
        for i, photo_name in enumerate(photo_items[:5], 1):
            photo_path = os.path.join(test_dir, photo_name)
            result = tester.test_file(photo_path)
            if result:
                results.append(result)
        
        if results:
            print("\n" + "=" * 60)
            print(f"✅ 成功测试了 {len(results)} 张照片")
            print("=" * 60)
        else:
            print("\n⚠️  未能成功解析任何照片")
    else:
        print("\n⚠️  在测试目录中未找到JPG文件")

if __name__ == "__main__":
    main()
