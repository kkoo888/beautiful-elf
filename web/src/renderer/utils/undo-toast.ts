/** 操作撤销 Toast */

import { message } from 'antd'
import React from 'react'

/**
 * 显示带撤销操作的 Toast
 * @param msg - 提示消息
 * @param onUndo - 撤销回调
 * @param duration - 显示时长（秒），默认 30
 */
export function showUndoToast(
  msg: string,
  onUndo: () => void,
  duration: number = 30
): void {
  const key = `undo_${Date.now()}`
  message.info({
    content: React.createElement('span', {}, [
      msg,
      React.createElement(
        'a',
        {
          key: 'undo',
          style: { marginLeft: 8, cursor: 'pointer' },
          onClick: () => {
            onUndo()
            message.destroy(key)
          },
        },
        '撤销'
      ),
    ]),
    key,
    duration,
  })
}
