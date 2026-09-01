import 'axios'

declare module 'axios' {
  interface AxiosRequestConfig {
    /**
     * 抑制该请求失败时的全局错误 toast（见 `src/api/client.ts` 响应拦截器）。
     *
     * 用于「失败是预期路径」的请求——例如首次查询尚不存在的功能拆分结果
     * （后端返回 404 + msg「功能拆分结果」），由调用方自行处理，
     * 不应把资源名当成错误文案弹给用户（V4.0 生产黑盒复盘 P1-3）。
     */
    suppressErrorToast?: boolean
  }
}
