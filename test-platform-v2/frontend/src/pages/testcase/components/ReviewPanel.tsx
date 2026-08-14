import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Textarea } from '@/components/ui/textarea'
import type { TestCaseReviewTransition } from '@/types'

const REVIEW_LABELS: Record<string, string> = { draft: '草稿', submitted: '已提交', approved: '已通过', rejected: '已驳回' }
const REVIEW_TONES: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  draft: 'neutral',
  submitted: 'info',
  approved: 'success',
  rejected: 'danger',
}

interface ReviewPanelProps {
  reviewStatus: string
  reviewComment: string
  setReviewComment: (v: string) => void
  reviewing: boolean
  reviewHistory: TestCaseReviewTransition[]
  onReview: (action: string) => void
}

export default function ReviewPanel({
  reviewStatus, reviewComment, setReviewComment, reviewing,
  reviewHistory, onReview,
}: ReviewPanelProps) {
  const statusLabel = REVIEW_LABELS[reviewStatus] || reviewStatus
  const statusTone = REVIEW_TONES[reviewStatus] || 'neutral'

  return (
    <div className="max-h-[60vh] overflow-y-auto space-y-4">
      {/* Current status */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">当前评审状态：</span>
        <Badge tone={statusTone}>{statusLabel}</Badge>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        {(reviewStatus === 'draft' || reviewStatus === 'rejected') && (
          <Button size="sm" onClick={() => onReview('submit')} disabled={reviewing}>
            {reviewing ? '提交中...' : '提交评审'}
          </Button>
        )}
        {reviewStatus === 'submitted' && (
          <>
            <Button size="sm" variant="primary" onClick={() => onReview('approve')} disabled={reviewing}>
              {reviewing ? '处理中...' : '通过'}
            </Button>
            <Button size="sm" variant="danger" onClick={() => onReview('reject')} disabled={reviewing}>
              {reviewing ? '处理中...' : '驳回'}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onReview('withdraw')} disabled={reviewing}>
              撤回
            </Button>
          </>
        )}
        {reviewStatus === 'approved' && (
          <p className="text-sm text-muted-foreground">此用例已评审通过。修改用例内容将重置评审状态为草稿。</p>
        )}
      </div>

      {/* Comment */}
      {reviewStatus !== 'approved' && (
        <div>
          <label htmlFor="review-comment" className="mb-1 block text-sm font-medium">评审意见</label>
          <Textarea
            id="review-comment"
            rows={3}
            placeholder="输入评审意见（可选）"
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
          />
        </div>
      )}

      {/* Review history */}
      <div>
        <h4 className="text-sm font-semibold mb-2">评审历史</h4>
        {reviewHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无评审记录</p>
        ) : (
          <div className="space-y-2">
            {reviewHistory.map((t) => (
              <div key={t.id} className="rounded-md border p-3 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <Badge tone={REVIEW_TONES[t.from_status] || 'neutral'} className="text-xs">
                    {t.from_label}
                  </Badge>
                  <span className="text-muted-foreground">→</span>
                  <Badge tone={REVIEW_TONES[t.to_status] || 'neutral'} className="text-xs">
                    {t.to_label}
                  </Badge>
                  <span className="text-muted-foreground ml-auto text-xs">
                    {t.reviewer_name} · {t.created_at ? new Date(t.created_at).toLocaleString('zh-CN') : ''}
                  </span>
                </div>
                {t.comment && (
                  <p className="text-muted-foreground text-xs mt-1">意见: {t.comment}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
