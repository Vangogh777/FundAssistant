import client from './client';

export const fundApi = {
  // 基金搜索
  search: (keyword: string) => client.get('/funds/search', { params: { keyword } }),

  // 持仓管理
  getPortfolios: () => client.get('/portfolio'),
  batchAddPortfolios: (funds: any[]) => client.post('/portfolio/batch', funds),
  importCsv: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post('/portfolio/import-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  addPortfolio: (data: {
    fund_code: string;
    shares?: number;
    cost_per_share?: number;
    investment_amount?: number;
    current_value?: number;
    current_profit?: number;
    buy_date?: string;
    buy_time?: string;
    fee?: number;
    note?: string;
  }) => client.post('/portfolio', data),
  updatePortfolio: (id: number, data: Record<string, unknown>) =>
    client.put(`/portfolio/${id}`, data),
  deletePortfolio: (id: number) => client.delete(`/portfolio/${id}`),
  getPortfolioAnalysis: (days?: number) => client.get('/portfolio/analysis', { params: { days } }),
  getPortfolioHistory: (id: number) => client.get(`/portfolio/${id}/history`),

  // 净值历史
  getNavHistory: (fund_code: string, days?: number) =>
    client.get(`/funds/${fund_code}/nav`, { params: { days } }),

  // 市场行情
  getMarketIndices: () => client.get('/market/indices'),
  getNorthFlow: () => client.get('/market/north-flow'),
  getMainFlow: () => client.get('/market/main-flow'),
  getSectorFlow: (top?: number) => client.get('/market/sector-flow', { params: { top } }),

  // 定投计划
  getDripPlans: () => client.get('/drip'),
  createDripPlan: (data: {
    fund_code: string;
    amount: number;
    frequency: string;
    day_of_week?: number;
    day_of_month?: number;
    next_run_date: string;
  }) => client.post('/drip', data),
  updateDripPlan: (id: number, data: Record<string, unknown>) =>
    client.put(`/drip/${id}`, data),
  deleteDripPlan: (id: number) => client.delete(`/drip/${id}`),

  // AI 分析
  analyzeFund: (data: {
    fund_code: string;
    model?: string;
    periods?: string[];
    include_sentiment?: boolean;
    include_technical?: boolean;
  }) => client.post('/analysis/ai', data),

  // 通知渠道
  getChannels: () => client.get('/notification/channels'),
  createChannel: (data: { channel_type: string; config: Record<string, unknown> }) =>
    client.post('/notification/channels', data),
  deleteChannel: (id: number) => client.delete(`/notification/channels/${id}`),
};
