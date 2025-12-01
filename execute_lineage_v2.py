# -*- coding: utf-8 -*-
"""
数据血缘提取执行脚本 v2.0
优化版本，支持更好的配置管理和错误处理
"""

import sys
import time
import logging
from datetime import datetime
import get_etl_add_lineage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lineage_extraction.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class LineageExtractor:
    """血缘提取器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.stats = {
            'dolphinscheduler': {'success': 0, 'fail': 0, 'skip': 0},
            'streampark': {'success': 0, 'fail': 0, 'skip': 0},
            'canal': {'success': 0, 'fail': 0, 'skip': 0},
        }
    
    def run(self, platforms=None):
        """
        运行血缘提取
        
        Args:
            platforms: 要提取的平台列表，None 表示全部
                      可选值: ['dolphinscheduler', 'streampark', 'canal']
        """
        self.start_time = datetime.now()
        logger.info("="*60)
        logger.info("数据血缘提取开始")
        logger.info(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        if platforms is None:
            platforms = ['dolphinscheduler', 'streampark', 'canal']
        
        # 提取各平台血缘
        for platform in platforms:
            self._extract_platform(platform)
        
        self.end_time = datetime.now()
        self._print_summary()
    
    def _extract_platform(self, platform):
        """提取指定平台的血缘"""
        logger.info(f"\n{'='*60}")
        logger.info(f"开始提取 {platform.upper()} 血缘")
        logger.info(f"{'='*60}")
        
        try:
            if platform == 'dolphinscheduler':
                self._extract_dolphinscheduler()
            elif platform == 'streampark':
                self._extract_streampark()
            elif platform == 'canal':
                self._extract_canal()
            else:
                logger.warning(f"未知平台: {platform}")
        
        except Exception as exc:
            logger.error(f"{platform} 血缘提取失败: {exc}")
            import traceback
            traceback.print_exc()
    
    def _extract_dolphinscheduler(self):
        """提取 DolphinScheduler 血缘"""
        try:
            extractor = get_etl_add_lineage.GetDolphinSchedulerData()
            extractor.get_data_add_lineage()
            logger.info("✓ DolphinScheduler 血缘提取完成")
        except Exception as exc:
            logger.error(f"✗ DolphinScheduler 血缘提取失败: {exc}")
            raise
    
    def _extract_streampark(self):
        """提取 StreamPark 血缘"""
        try:
            extractor = get_etl_add_lineage.GetStreamParkData()
            extractor.get_data_add_lineage()
            logger.info("✓ StreamPark 血缘提取完成")
        except Exception as exc:
            logger.error(f"✗ StreamPark 血缘提取失败: {exc}")
            raise
    
    def _extract_canal(self):
        """提取 Canal 血缘"""
        try:
            extractor = get_etl_add_lineage.GetCanalData()
            extractor.get_data_add_lineage()
            logger.info("✓ Canal 血缘提取完成")
        except Exception as exc:
            logger.error(f"✗ Canal 血缘提取失败: {exc}")
            raise
    
    def _print_summary(self):
        """打印执行总结"""
        duration = (self.end_time - self.start_time).total_seconds()
        
        logger.info("\n" + "="*60)
        logger.info("数据血缘提取完成")
        logger.info("="*60)
        logger.info(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"总耗时: {duration:.2f} 秒")
        logger.info("="*60)


def main():
    """主函数"""
    extractor = LineageExtractor()
    
    # 可以选择性地提取某些平台
    # extractor.run(platforms=['dolphinscheduler'])  # 只提取 DolphinScheduler
    # extractor.run(platforms=['streampark'])  # 只提取 StreamPark
    # extractor.run(platforms=['canal'])  # 只提取 Canal
    
    # 提取所有平台
    extractor.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n用户中断执行")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"执行失败: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
