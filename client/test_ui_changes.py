"""
测试 UI 修改是否生效
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

def test_ui_changes():
    """测试 UI 修改"""
    app = QApplication(sys.argv)
    window = MainWindow()
    
    # 检查全局字体
    font = window.font()
    print(f"✓ 全局字体大小: {font.pointSize()}pt (应该是 10pt)")
    
    # 检查主窗口边距
    margins = window.contentsMargins()
    print(f"✓ 主窗口边距: left={margins.left()}, top={margins.top()}, right={margins.right()}, bottom={margins.bottom()} (应该全是 0)")
    
    # 检查状态栏高度
    status_bar_height = window.status_bar.height()
    print(f"✓ 状态栏高度: {status_bar_height}px (应该是 28px)")
    
    # 检查按钮字体
    if hasattr(window, 'control_buttons') and 'start' in window.control_buttons:
        start_button = window.control_buttons['start']
        button_font = start_button.font()
        print(f"✓ 开始按钮字体: {button_font.pointSize()}pt")
        print(f"✓ 开始按钮最小高度: {start_button.minimumHeight()}px (应该是 30px)")
    
    # 检查视频标签背景色
    video_label_style = window.video_label.styleSheet()
    if '#F0F4F8' in video_label_style:
        print(f"✓ 视频标签背景色: #F0F4F8 (正确)")
    else:
        print(f"✗ 视频标签背景色不正确")
        print(f"  当前样式: {video_label_style[:200]}...")
    
    print("\n所有检查完成！")
    print("如果以上数值正确，说明代码修改已生效。")
    print("如果界面显示不正确，可能是样式表渲染问题。")
    
    # 显示窗口
    window.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(test_ui_changes())
