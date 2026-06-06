import React, { useState } from 'react'
import { Row, Col, Card, List, Typography, Button, Popconfirm, Tag } from 'antd'
import { DeleteOutlined, FieldTimeOutlined } from '@ant-design/icons'
import OcrUploader from './components/ocr-uploader'
import OcrResultView from './components/ocr-result'
import OcrProgressView from './components/ocr-progress'
import { useOcr } from './hooks/use-ocr'
import styles from './ocr-panel.module.css'

const { Title, Text } = Typography

const OcrPanel: React.FC = () => {
  const { progress, result, history, recognize, clearHistory } = useOcr()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const handleImageReady = (base64: string, fileName: string) => {
    setPreviewUrl(base64)
    recognize(base64, fileName)
  }

  const isRecognizing = progress.status === 'loading'

  return (
    <div className={styles.panel}>
      <Title level={3}>OCR 文字识别</Title>

      <Row gutter={[24, 24]}>
        {/* 左侧：上传 / 预览 */}
        <Col xs={24} md={12}>
          <Card title="图片上传" className={styles.card}>
            <OcrUploader onImageReady={handleImageReady} disabled={isRecognizing} />

            {previewUrl && (
              <div className={styles.preview}>
                <img src={previewUrl} alt="预览" className={styles.previewImg} />
              </div>
            )}

            <OcrProgressView progress={progress} />
          </Card>
        </Col>

        {/* 右侧：识别结果 */}
        <Col xs={24} md={12}>
          <Card title="识别结果" className={styles.card}>
            {result ? (
              <OcrResultView result={result} />
            ) : (
              <div className={styles.empty}>
                <Text type="secondary">上传图片后开始识别</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 底部：识别历史 */}
      <Card
        title="识别历史"
        className={styles.historyCard}
        extra={
          history.length > 0 && (
            <Popconfirm title="确认清空历史？" onConfirm={clearHistory}>
              <Button size="small" danger icon={<DeleteOutlined />}>
                清空
              </Button>
            </Popconfirm>
          )
        }
      >
        {history.length === 0 ? (
          <Text type="secondary">暂无识别历史</Text>
        ) : (
          <List
            dataSource={history}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <>
                      <Text strong>{item.imageName}</Text>
                      <Tag color="blue" style={{ marginLeft: 8 }}>
                        置信度 {Math.round(item.confidence * 100)}%
                      </Tag>
                    </>
                  }
                  description={
                    <>
                      <Text ellipsis style={{ maxWidth: 400 }}>
                        {item.text.slice(0, 80)}...
                      </Text>
                      <br />
                      <Text type="secondary">
                        <FieldTimeOutlined style={{ marginRight: 4 }} />
                        {new Date(item.createdAt).toLocaleString()}
                      </Text>
                    </>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}

export default OcrPanel
