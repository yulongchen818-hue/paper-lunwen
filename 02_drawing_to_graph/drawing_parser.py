"""
DWG图纸解析服务 - 让API读懂图纸内容
使用 ezdxf 库解析CAD文件，提取尺寸、实体、图层信息
"""
import ezdxf
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class DrawingParser:
    """CAD图纸解析器"""
    
    def __init__(self, base_path: str = None):
        """
        初始化解析器
        
        Args:
            base_path: CAD图纸根目录，默认指向图纸目录
        """
        if base_path is None:
            self.base_path = Path("<DRAWING_ROOT>")
        else:
            self.base_path = Path(base_path)
    
    def parse_dwg(self, file_path: str) -> Dict[str, Any]:
        """
        解析DWG文件，提取关键信息
        
        注意：ezdxf只能直接读取DXF格式。
        对于DWG文件，需要先转换为DXF或用ODA File Converter
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return {"error": f"文件不存在: {file_path}"}
        
        try:
            # ezdxf 读取 DXF 文件
            # DWG 需要先用 ODA File Converter 转换
            doc = ezdxf.readfile(str(full_path))
            
            msp = doc.modelspace()
            
            # 提取基本信息
            info = {
                "fileName": full_path.name,
                "filePath": str(file_path),
                "dwgVersion": doc.dxfversion,
                "layers": [],
                "entities": {
                    "lines": 0,
                    "circles": 0,
                    "arcs": 0,
                    "polylines": 0,
                    "dimensions": 0,
                    "texts": 0,
                    "others": 0
                },
                "dimensions": [],  # 提取的尺寸标注
                "texts": [],       # 提取的文字
                "boundingBox": None
            }
            
            # 图层信息
            for layer in doc.layers:
                info["layers"].append({
                    "name": layer.dxf.name,
                    "color": layer.dxf.color,
                    "linetype": layer.dxf.linetype
                })
            
            # 统计实体类型
            for entity in msp:
                entity_type = entity.dxftype()
                
                if entity_type == "LINE":
                    info["entities"]["lines"] += 1
                elif entity_type == "CIRCLE":
                    info["entities"]["circles"] += 1
                    # 提取圆信息（可能是孔洞）
                    info["dimensions"].append({
                        "type": "circle",
                        "center": (entity.dxf.center.x, entity.dxf.center.y),
                        "radius": entity.dxf.radius
                    })
                elif entity_type == "ARC":
                    info["entities"]["arcs"] += 1
                elif entity_type in ["LWPOLYLINE", "POLYLINE"]:
                    info["entities"]["polylines"] += 1
                elif entity_type in ["DIMENSION", "ARC_DIMENSION"]:
                    info["entities"]["dimensions"] += 1
                    # 提取尺寸标注
                    try:
                        info["dimensions"].append({
                            "type": "dimension",
                            "text": entity.dxf.text,
                            "actualMeasurement": entity.dxf.actual_measurement if hasattr(entity.dxf, 'actual_measurement') else None,
                            "layer": entity.dxf.layer
                        })
                    except:
                        pass
                elif entity_type in ["TEXT", "MTEXT"]:
                    info["entities"]["texts"] += 1
                    # 提取文字（可能是标注、说明）
                    try:
                        text_content = entity.dxf.text if hasattr(entity.dxf, 'text') else entity.text
                        info["texts"].append({
                            "content": text_content[:100],  # 限制长度
                            "position": (entity.dxf.insert.x, entity.dxf.insert.y) if hasattr(entity.dxf, 'insert') else None,
                            "layer": entity.dxf.layer
                        })
                    except:
                        pass
                else:
                    info["entities"]["others"] += 1
            
            # 尝试计算包围盒
            try:
                extents = msp.extents()
                info["boundingBox"] = {
                    "min": (extents.extmin.x, extents.extmin.y),
                    "max": (extents.extmax.x, extents.extmax.y),
                    "width": extents.extmax.x - extents.extmin.x,
                    "height": extents.extmax.y - extents.extmin.y
                }
            except:
                pass
            
            return info
            
        except ezdxf.DXFStructureError as e:
            return {"error": f"DXF文件结构错误: {str(e)}"}
        except Exception as e:
            return {"error": f"解析失败: {str(e)}"}
    
    def extract_beam_parameters(self, file_path: str) -> Dict[str, Any]:
        """
        专门针对梁段图纸提取参数
        尝试从尺寸标注中提取：长度、宽度、高度、板厚等
        """
        result = self.parse_dwg(file_path)
        
        if "error" in result:
            return result
        
        # 分析提取的参数
        params = {
            "possibleDimensions": [],
            "detectedCircles": [],  # 可能是螺栓孔
            "annotations": []
        }
        
        # 从文字中提取数字（可能是尺寸）
        for text in result.get("texts", []):
            content = text.get("content", "")
            # 匹配类似 "1200"、"t=12"、"δ20" 等模式
            import re
            
            # 查找尺寸数字
            numbers = re.findall(r'\d+\.?\d*', content)
            if numbers:
                params["possibleDimensions"].extend([float(n) for n in numbers])
            
            # 查找厚度标注
            thickness = re.findall(r'[tδ]=(\d+)', content)
            if thickness:
                params["annotations"].append({"type": "thickness", "value": thickness[0]})
        
        # 统计圆（可能是螺栓孔）
        for dim in result.get("dimensions", []):
            if dim.get("type") == "circle":
                params["detectedCircles"].append({
                    "radius": dim["radius"],
                    "diameter": dim["radius"] * 2
                })
        
        result["extractedParameters"] = params
        return result
    
    def compare_drawings(self, file1: str, file2: str) -> Dict[str, Any]:
        """对比两张图纸的相似度"""
        info1 = self.parse_dwg(file1)
        info2 = self.parse_dwg(file2)
        
        if "error" in info1 or "error" in info2:
            return {"error": "无法对比，解析失败"}
        
        return {
            "file1": file1,
            "file2": file2,
            "similarity": {
                "layerCount": len(info1["layers"]) == len(info2["layers"]),
                "entityTypes": info1["entities"] == info2["entities"],
                "sizeRatio": self._calc_size_ratio(info1, info2)
            }
        }
    
    def _calc_size_ratio(self, info1: Dict, info2: Dict) -> Optional[float]:
        """计算图纸尺寸比例"""
        bb1 = info1.get("boundingBox")
        bb2 = info2.get("boundingBox")
        
        if bb1 and bb2:
            area1 = bb1["width"] * bb1["height"]
            area2 = bb2["width"] * bb2["height"]
            return round(area1 / area2, 2) if area2 > 0 else None
        return None


# 快速测试
if __name__ == "__main__":
    parser = DrawingParser()
    
    print("=== DWG图纸解析测试 ===")
    print(f"图纸目录: {parser.base_path}")
    print()
    
    # 注意：这个示例需要DXF文件或转换后的文件
    # 实际的DWG文件需要先用转换工具处理
    
    print("说明：")
    print("1. ezdxf 库可以直接读取 DXF 文件")
    print("2. 对于 DWG 文件，需要先转换为 DXF")
    print("3. 转换工具：ODA File Converter (免费) 或 AutoCAD")
    print()
    print("使用方法：")
    print("  from drawing_parser import DrawingParser")
    print("  parser = DrawingParser()")
    print("  result = parser.parse_dwg('主桥/1图纸/D-01-05.dxf')")
