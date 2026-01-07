# -*- coding: utf-8 -*-
"""
OpenMetadata 下游血缘导出工具
获取指定表的所有下游表，逐级遍历，导出到 Excel

功能：
- 从指定表开始，递归获取所有下游表
- 按层级显示下游节点
- 最后一列显示完整链路（用 -> 连接）
"""

import sys
import os
import io
import argparse
import requests
import urllib3
import pandas as pd
from datetime import datetime
from collections import deque

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class DownstreamLineageExporter:
    """下游血缘导出器"""
    
    def __init__(self, base_url, jwt_token):
        self.base_url = base_url.rstrip('/')
        self.jwt_token = jwt_token
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        })
    
    def get_table_info(self, table_fqn):
        """获取表信息"""
        url = f"{self.base_url}/v1/tables/name/{table_fqn}"
        resp = self.session.get(url)
        if resp.status_code == 200:
            return resp.json()
        print(f"⚠️  获取表信息失败: {table_fqn}, 状态码: {resp.status_code}")
        return None
    
    def get_lineage(self, table_fqn, downstream_depth=10):
        """获取表的血缘关系"""
        url = f"{self.base_url}/v1/lineage/getLineage"
        params = {
            "fqn": table_fqn,
            "type": "table",
            "upstreamDepth": 0,
            "downstreamDepth": downstream_depth
        }
        
        resp = self.session.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        
        print(f"⚠️  获取血缘失败: {resp.status_code}")
        return None
    
    def parse_lineage_graph(self, lineage_data, root_fqn):
        """
        解析血缘图，构建下游关系
        
        Returns:
            nodes: {node_id: node_info}
            downstream_map: {from_id: [to_ids]}
        """
        if not lineage_data:
            return {}, {}
        
        # 节点信息 - nodes 是字典，key 是节点 ID
        nodes = {}
        raw_nodes = lineage_data.get('nodes', {})
        
        if isinstance(raw_nodes, dict):
            for node_id, node_info in raw_nodes.items():
                if isinstance(node_info, dict):
                    nodes[node_id] = {
                        'id': node_info.get('id', node_id),
                        'fqn': node_info.get('fullyQualifiedName', ''),
                        'name': node_info.get('name', ''),
                        'type': node_info.get('type', '')
                    }
        
        # 下游边关系 - downstreamEdges 也是字典
        downstream_map = {}  # {from_id: [to_ids]}
        raw_edges = lineage_data.get('downstreamEdges', {})
        
        if isinstance(raw_edges, dict):
            for edge_key, edge_info in raw_edges.items():
                if isinstance(edge_info, dict):
                    # 边的格式: fromEntity 和 toEntity 都是对象
                    from_entity = edge_info.get('fromEntity', {})
                    to_entity = edge_info.get('toEntity', {})
                    
                    from_id = from_entity.get('id') if isinstance(from_entity, dict) else None
                    to_id = to_entity.get('id') if isinstance(to_entity, dict) else None
                    
                    # 同时把节点信息加入 nodes
                    if from_id and isinstance(from_entity, dict):
                        if from_id not in nodes:
                            nodes[from_id] = {
                                'id': from_id,
                                'fqn': from_entity.get('fullyQualifiedName', ''),
                                'name': from_entity.get('name', ''),
                                'type': from_entity.get('type', '')
                            }
                    
                    if to_id and isinstance(to_entity, dict):
                        if to_id not in nodes:
                            nodes[to_id] = {
                                'id': to_id,
                                'fqn': to_entity.get('fullyQualifiedName', ''),
                                'name': to_entity.get('name', ''),
                                'type': to_entity.get('type', '')
                            }
                    
                    if from_id and to_id:
                        if from_id not in downstream_map:
                            downstream_map[from_id] = []
                        if to_id not in downstream_map[from_id]:
                            downstream_map[from_id].append(to_id)
        
        return nodes, downstream_map
    
    def find_root_id(self, nodes, root_fqn):
        """找到根节点 ID"""
        for node_id, node_info in nodes.items():
            if node_info.get('fqn') == root_fqn:
                return node_id
        return None
    
    def traverse_downstream_bfs(self, nodes, downstream_map, root_id, root_fqn, max_depth=10):
        """
        BFS 遍历所有下游节点
        
        Returns:
            list: [(depth, fqn, name, path)]
        """
        results = []
        visited = set()
        
        # (node_id, depth, path_fqns)
        queue = deque([(root_id, 0, [root_fqn])])
        visited.add(root_id)
        
        while queue:
            current_id, depth, path = queue.popleft()
            current_node = nodes.get(current_id, {})
            
            # 添加到结果（跳过根节点本身）
            if depth > 0:
                results.append({
                    'depth': depth,
                    'fqn': current_node.get('fqn', ''),
                    'name': current_node.get('name', ''),
                    'path': path.copy()
                })
            
            # 获取下游节点
            if depth < max_depth:
                for next_id in downstream_map.get(current_id, []):
                    if next_id not in visited:
                        visited.add(next_id)
                        next_node = nodes.get(next_id, {})
                        next_fqn = next_node.get('fqn', '')
                        new_path = path + [next_fqn]
                        queue.append((next_id, depth + 1, new_path))
        
        return results
    
    def get_short_name(self, fqn):
        """获取简短名称（schema.table）"""
        if not fqn:
            return ''
        parts = fqn.split('.')
        if len(parts) >= 2:
            return f"{parts[-2]}.{parts[-1]}"
        return fqn
    
    def traverse_downstream(self, root_fqn, max_depth=10):
        """遍历所有下游节点"""
        print(f"\n🔍 获取 {root_fqn} 的血缘关系...")
        
        lineage_data = self.get_lineage(root_fqn, max_depth)
        if not lineage_data:
            print("❌ 无法获取血缘数据")
            return []
        
        nodes, downstream_map = self.parse_lineage_graph(lineage_data, root_fqn)
        
        print(f"   节点数: {len(nodes)}")
        print(f"   边数: {sum(len(v) for v in downstream_map.values())}")
        
        # 找到根节点 ID
        root_id = self.find_root_id(nodes, root_fqn)
        
        if not root_id:
            print(f"❌ 未找到根节点: {root_fqn}")
            # 尝试从表信息获取 ID
            table_info = self.get_table_info(root_fqn)
            if table_info:
                root_id = table_info.get('id')
                if root_id:
                    nodes[root_id] = {
                        'id': root_id,
                        'fqn': root_fqn,
                        'name': table_info.get('name', ''),
                        'type': 'table'
                    }
        
        if not root_id:
            print(f"❌ 仍然无法找到根节点")
            return []
        
        # BFS 遍历
        results = self.traverse_downstream_bfs(nodes, downstream_map, root_id, root_fqn, max_depth)
        
        print(f"✅ 找到 {len(results)} 个下游节点")
        return results
    
    def export_to_excel(self, root_fqn, output_dir='.', max_depth=10):
        """导出到 Excel"""
        print(f"\n🚀 开始导出下游血缘: {root_fqn}")
        
        # 遍历下游
        downstream_nodes = self.traverse_downstream(root_fqn, max_depth)
        
        if not downstream_nodes:
            print("⚠️  没有找到下游节点")
            return None
        
        # 确定最大深度
        actual_max_depth = max(node['depth'] for node in downstream_nodes)
        print(f"📊 最大深度: {actual_max_depth} 层")
        
        # 构建数据
        rows = []
        for node in downstream_nodes:
            row = {
                '序号': len(rows) + 1,
                '深度': node['depth'],
            }
            
            # 添加每一层的列
            for i in range(1, actual_max_depth + 1):
                col_name = f'第{i}层下游'
                if i < len(node['path']):
                    row[col_name] = self.get_short_name(node['path'][i])
                else:
                    row[col_name] = ''
            
            # 完整链路
            path_short = [self.get_short_name(p) for p in node['path']]
            row['完整链路'] = ' -> '.join(path_short)
            
            # 完整 FQN
            row['完整FQN'] = node['fqn']
            
            rows.append(row)
        
        # 按深度和名称排序
        rows.sort(key=lambda x: (x['深度'], x.get('第1层下游', ''), x.get('第2层下游', '')))
        
        # 重新编号
        for i, row in enumerate(rows, 1):
            row['序号'] = i
        
        # 创建 DataFrame
        df = pd.DataFrame(rows)
        
        # 导出
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        root_short = self.get_short_name(root_fqn).replace('.', '_')
        filename = os.path.join(output_dir, f"Downstream_Lineage_{root_short}_{timestamp}.xlsx")
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='下游血缘', index=False)
                
                # 调整列宽
                from openpyxl.utils import get_column_letter
                worksheet = writer.sheets['下游血缘']
                
                for idx, col in enumerate(df.columns, 1):
                    try:
                        max_length = max(
                            df[col].astype(str).apply(len).max(),
                            len(str(col))
                        )
                        adjusted_width = min(max(max_length + 2, 10), 80)
                        column_letter = get_column_letter(idx)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                    except:
                        pass
            
            print(f"\n✅ 导出成功: {filename}")
            print(f"📊 下游节点数: {len(rows)}")
            print(f"📊 最大深度: {actual_max_depth} 层")
            
            # 打印预览
            print(f"\n📋 预览 (前10条):")
            for row in rows[:10]:
                print(f"   {row['完整链路']}")
            
            return filename
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    parser = argparse.ArgumentParser(description='OpenMetadata 下游血缘导出工具')
    parser.add_argument('--host', default="https://openmetadata.changdu.vip/api", help='OpenMetadata API 地址')
    parser.add_argument('--token', help='JWT Token')
    parser.add_argument('--table', required=True, help='表的完全限定名 (FQN)')
    parser.add_argument('--output', default='.', help='输出目录')
    parser.add_argument('--max-depth', type=int, default=10, help='最大遍历深度')
    
    args = parser.parse_args()
    
    # 默认 token
    if not args.token:
        args.token = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImxpbmVhZ2UtYm90Iiwicm9sZXMiOlsiTGluZWFnZUJvdFJvbGUiXSwiZW1haWwiOiJsaW5lYWdlLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3NjU3OTQ2OTQsImV4cCI6bnVsbH0.YSFXrR-DzaeBBNtni_rc3Hw1j2rA29oj038n7llTr-8zLcf2g-MEqd1CVhQwrq4rrMgEmk3go4T3diHvGbZ5LLP-Z_-nl90ZUuC2xIXH2_m7LrMnIbuQxvrbtVAJz_X8AEK9im5rm9OQFUytPcWk0Yy0Bji4_8IfjpkhVxXNmR4ZIPyz2tVTkRKWvQ5HDCCuArhLw3fTxAuZYWazSzBVFjfv_WaSpth37C8ftD-JS3s9UT-QPog7zMjTehXFHx9q_pcegoSmVQST1P15I01r5S5bv_IDHnrqi-7bKJGOFwBbx0gtPfzc1fWIKDY57IEsVE1F4ijZxazhfsDTJtCs5Q"
    
    print("="*60)
    print("OpenMetadata 下游血缘导出工具")
    print("="*60)
    print(f"源表: {args.table}")
    print(f"最大深度: {args.max_depth}")
    print(f"输出目录: {args.output}")
    print("="*60)
    
    exporter = DownstreamLineageExporter(args.host, args.token)
    filename = exporter.export_to_excel(args.table, args.output, args.max_depth)
    
    if filename:
        print("\n" + "="*60)
        print("✅ 导出完成！")
        print("="*60)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
