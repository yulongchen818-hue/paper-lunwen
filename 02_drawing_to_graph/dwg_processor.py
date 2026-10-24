"""
DWG图纸自动处理模块
功能：DWG→DXF转换 → 解析提取尺寸 → 存入知识图谱
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import shutil


class DWGProcessor:
    """DWG图纸处理器 - 自动转换并解析"""
    
    def __init__(self, 
                 dwg_base_path: str = None,
                 dxf_output_path: str = None,
                 oda_converter_path: str = None):
        """
        初始化处理器
        
        Args:
            dwg_base_path: DWG图纸根目录
            dxf_output_path: DXF转换输出目录
            oda_converter_path: ODA File Converter可执行文件路径
        """
        self.dwg_base_path = Path(dwg_base_path) if dwg_base_path else \
            Path("<DRAWING_ROOT>")
        
        self.dxf_output_path = Path(dxf_output_path) if dxf_output_path else \
            self.dwg_base_path.parent / "DXF"
        
        self.oda_converter = oda_converter_path or self._find_oda_converter()
        
        # 确保输出目录存在
        self.dxf_output_path.mkdir(parents=True, exist_ok=True)
    
    def _find_oda_converter(self) -> Optional[str]:
        """查找ODA File Converter"""
        possible_paths = [
            "/usr/bin/odafileconverter",
            "/usr/local/bin/odafileconverter",
            "/opt/odafileconverter/odafileconverter",
            "odafileconverter",  # 在PATH中
            "C:/Program Files/ODA/ODAFileConverter/ODAFileConverter.exe",
            "C:/ODA/ODAFileConverter.exe",
        ]
        
        for path in possible_paths:
            if shutil.which(path) or os.path.exists(path):
                return path
        
        return None
    
    def check_oda_installer(self) -> Dict[str, Any]:
        """检查ODA转换器状态"""
        if self.oda_converter:
            return {
                "installed": True,
                "path": self.oda_converter
            }
        
        return {
            "installed": False,
            "download_url": "https://www.opendesign.com/guestfiles/oda_file_converter",
            "install_guide": {
                "Linux": "下载Linux版本，解压后运行 install.sh",
                "Windows": "下载Windows版本，运行安装程序",
                "Docker": "docker run -v $(pwd):/drawings opendesign/odafileconverter"
            }
        }
    
    def convert_dwg_to_dxf(self, dwg_file: str, output_dir: str = None) -> Tuple[bool, str]:
        """
        将单个DWG文件转换为DXF
        
        Returns:
            (success: bool, message: str)
        """
        if not self.oda_converter:
            return False, "ODA File Converter未安装"
        
        dwg_path = Path(dwg_file)
        if not dwg_path.exists():
            return False, f"文件不存在: {dwg_file}"
        
        out_dir = Path(output_dir) if output_dir else self.dxf_output_path
        out_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # ODA File Converter 命令行格式：
            # ODAFileConverter <input folder> <output folder> <version> <output type> <recursive> <audit>
            cmd = [
                self.oda_converter,
                str(dwg_path.parent),  # 输入目录
                str(out_dir),          # 输出目录
                "ACAD2018",            # 版本
                "DXF",                 # 输出格式
                "0",                   # 不递归
                "1"                    # 审计
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if result.returncode == 0:
                # 检查输出文件是否生成
                dxf_name = dwg_path.stem + ".dxf"
                dxf_path = out_dir / dxf_name
                
                if dxf_path.exists():
                    return True, str(dxf_path)
                else:
                    return False, "转换完成但未找到输出文件"
            else:
                return False, f"转换失败: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "转换超时"
        except Exception as e:
            return False, f"转换异常: {str(e)}"
    
    def batch_convert(self, pattern: str = "*.dwg") -> Dict[str, Any]:
        """
        批量转换DWG文件
        
        Args:
            pattern: 文件匹配模式，如 "D-01-05*.dwg"
        
        Returns:
            转换结果统计
        """
        if not self.oda_converter:
            return {
                "success": False,
                "error": "ODA File Converter未安装",
                "setup_guide": self.check_oda_installer()
            }
        
        # 查找所有匹配的DWG文件
        dwg_files = list(self.dwg_base_path.rglob(pattern))
        
        results = {
            "total": len(dwg_files),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for dwg_file in dwg_files:
            success, msg = self.convert_dwg_to_dxf(dwg_file)
            
            results["details"].append({
                "file": str(dwg_file.name),
                "success": success,
                "message": msg
            })
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def extract_dimensions_from_dxf(self, dxf_file: str) -> Dict[str, Any]:
        """
        从DXF文件中提取尺寸信息
        
        Returns:
            包含尺寸、实体、图层信息的字典
        """
        try:
            import ezdxf
        except ImportError:
            return {
                "error": "ezdxf库未安装，请运行: pip install ezdxf",
                "install_command": "pip install ezdxf"
            }
        
        dxf_path = Path(dxf_file)
        if not dxf_path.exists():
            return {"error": f"文件不存在: {dxf_file}"}
        
        try:
            doc = ezdxf.readfile(str(dxf_path))
            msp = doc.modelspace()
            
            # 提取的尺寸数据
            dimensions = {
                "linear": [],      # 线性尺寸
                "diameters": [],   # 直径尺寸
                "radii": [],       # 半径尺寸
                "angles": [],      # 角度尺寸
                "texts": []        # 文字标注
            }
            
            # 统计实体
            entity_count = {
                "lines": 0,
                "circles": 0,
                "arcs": 0,
                "polylines": 0,
                "dimensions": 0,
                "texts": 0,
                "others": 0
            }
            
            # 图层列表
            layers = []
            for layer in doc.layers:
                layers.append({
                    "name": layer.dxf.name,
                    "color": layer.dxf.color
                })
            
            # 解析实体
            for entity in msp:
                etype = entity.dxftype()
                
                if etype == "LINE":
                    entity_count["lines"] += 1
                
                elif etype == "CIRCLE":
                    entity_count["circles"] += 1
                    # 提取圆信息
                    dimensions["radii"].append({
                        "value": entity.dxf.radius,
                        "center": [entity.dxf.center.x, entity.dxf.center.y],
                        "diameter": entity.dxf.radius * 2
                    })
                
                elif etype == "ARC":
                    entity_count["arcs"] += 1
                
                elif etype in ["LWPOLYLINE", "POLYLINE"]:
                    entity_count["polylines"] += 1
                
                elif etype in ["DIMENSION", "ARC_DIMENSION"]:
                    entity_count["dimensions"] += 1
                    # 提取尺寸标注
                    try:
                        dim_text = entity.dxf.text
                        actual_measurement = getattr(entity.dxf, 'actual_measurement', None)
                        
                        # 解析尺寸文字（如 "1200", "%%c20", "R150"）
                        import re
                        
                        dim_info = {
                            "text": dim_text,
                            "actual": actual_measurement,
                            "type": "unknown"
                        }
                        
                        # 判断尺寸类型
                        if dim_text and dim_text.startswith("R"):
                            dim_info["type"] = "radius"
                            match = re.search(r'R(\d+\.?\d*)', dim_text)
                            if match:
                                dim_info["value"] = float(match.group(1))
                        
                        elif dim_text and ("%%c" in dim_text or "Φ" in dim_text):
                            dim_info["type"] = "diameter"
                            match = re.search(r'(?:%%c|Φ)(\d+\.?\d*)', dim_text)
                            if match:
                                dim_info["value"] = float(match.group(1))
                        
                        else:
                            # 线性尺寸
                            match = re.search(r'(\d+\.?\d*)', dim_text or "")
                            if match:
                                dim_info["value"] = float(match.group(1))
                                dim_info["type"] = "linear"
                        
                        dimensions["linear"].append(dim_info)
                    
                    except Exception as e:
                        pass
                
                elif etype in ["TEXT", "MTEXT"]:
                    entity_count["texts"] += 1
                    # 提取文字
                    try:
                        text_content = entity.dxf.text if hasattr(entity.dxf, 'text') else entity.text
                        dimensions["texts"].append({
                            "content": text_content[:100],
                            "position": [entity.dxf.insert.x, entity.dxf.insert.y] if hasattr(entity.dxf, 'insert') else None
                        })
                    except:
                        pass
                
                else:
                    entity_count["others"] += 1
            
            # 计算包围盒
            bounding_box = None
            try:
                extents = msp.extents()
                bounding_box = {
                    "min": [extents.extmin.x, extents.extmin.y],
                    "max": [extents.extmax.x, extents.extmax.y],
                    "width": extents.extmax.x - extents.extmin.x,
                    "height": extents.extmax.y - extents.extmin.y,
                    "area": (extents.extmax.x - extents.extmin.x) * (extents.extmax.y - extents.extmin.y)
                }
            except:
                pass
            
            return {
                "fileName": dxf_path.name,
                "layers": layers,
                "entityCount": entity_count,
                "dimensions": dimensions,
                "boundingBox": bounding_box,
                "totalEntities": sum(entity_count.values())
            }
            
        except Exception as e:
            return {"error": f"解析失败: {str(e)}"}
    
    def process_drawing(self, drawing_no: str, kg_service=None) -> Dict[str, Any]:
        """
        处理单张图纸：转换+解析+存入知识图谱
        
        Args:
            drawing_no: 图号（如 D-01-05）
            kg_service: 知识图谱服务实例
        
        Returns:
            处理结果
        """
        # 1. 从知识图谱获取图纸路径
        if kg_service:
            drawing = kg_service.get_drawing_by_no(drawing_no)
            if not drawing:
                return {"error": f"图号 {drawing_no} 在知识图谱中不存在"}
            
            file_path = drawing.get("sb:filePath", "")
            dwg_file = self.dwg_base_path.parent / file_path
        else:
            # 尝试直接查找
            dwg_file = self.dwg_base_path / f"{drawing_no}.dwg"
        
        if not dwg_file.exists():
            return {"error": f"DWG文件不存在: {dwg_file}"}
        
        # 2. 转换为DXF
        success, dxf_path = self.convert_dwg_to_dxf(dwg_file)
        
        if not success:
            return {
                "error": "转换失败",
                "message": dxf_path,
                "setup_guide": self.check_oda_installer()
            }
        
        # 3. 解析DXF
        parse_result = self.extract_dimensions_from_dxf(dxf_path)
        
        return {
            "drawingNo": drawing_no,
            "dwgPath": str(dwg_file),
            "dxfPath": dxf_path,
            "parseResult": parse_result
        }
    
    def get_beam_dimensions(self, beam_segment: str) -> Dict[str, Any]:
        """
        获取梁段的关键尺寸
        
        Args:
            beam_segment: 梁段标识，如 "Z1", "C1", "主梁1"
        
        Returns:
            尺寸数据
        """
        # 映射梁段到图纸
        drawing_map = {
            # project-specific segment-to-drawing mapping removed; populate from your own drawing register
            "EXAMPLE_SEGMENT": "D-01-05"
        }
        
        drawing_no = drawing_map.get(beam_segment)
        if not drawing_no:
            return {"error": f"未知梁段: {beam_segment}", "knownSegments": list(drawing_map.keys())}
        
        return self.process_drawing(drawing_no)


# 快速测试
if __name__ == "__main__":
    processor = DWGProcessor()
    
    print("=== DWG图纸处理器 ===")
    print(f"DWG路径: {processor.dwg_base_path}")
    print(f"DXF输出: {processor.dxf_output_path}")
    print()
    
    # 检查ODA转换器
    oda_status = processor.check_oda_installer()
    print(f"ODA转换器: {'已安装' if oda_status['installed'] else '未安装'}")
    
    if oda_status['installed']:
        print(f"  路径: {oda_status['path']}")
    else:
        print(f"  下载地址: {oda_status['download_url']}")
        print(f"  安装方式:")
        for platform, guide in oda_status['install_guide'].items():
            print(f"    {platform}: {guide}")
    
    print()
    print("使用示例:")
    print("  processor = DWGProcessor()")
    print("  result = processor.process_drawing('D-01-05')")
    print("  dimensions = processor.get_beam_dimensions('Z1')")
