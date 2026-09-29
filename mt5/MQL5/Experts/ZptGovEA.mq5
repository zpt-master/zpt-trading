//+------------------------------------------------------------------+
//| ZptGovEA.mq5 - Risk-Governed Execution EA for ZptMaster          |
//| Reads governed signals from a shared file; enforces hard risk     |
//| rules ON THE BROKER SIDE (last line of defense); reports state.   |
//|                                                                   |
//| Files (MT5 Common\Files):                                         |
//|   zpt_signals.csv -> in : symbol,side,entry,stop,target,lots       |
//|   zpt_state.json  -> out: equity/balance/positions/agg risk/ts     |
//|                                                                   |
//| Hard rules (cannot be overridden by a signal):                    |
//|   * max risk per order <= InpMaxRiskPct of equity (default 1.5%)  |
//|   * MANDATORY stop-loss (rejects any order lacking one)           |
//|   * reward:risk >= InpMinRR (default 1.5)                         |
//|   * lot size hard cap InpMaxLots (default 5.0)                    |
//|   * max aggregate open risk <= InpMaxAggRiskPct (default 4%)      |
//|   * NO martingale / NO averaging into losers                     |
//| Install: copy to MT5/Data Folder/MQL5/Experts/ then compile.      |
//+------------------------------------------------------------------+
#property copyright "ZptMaster"
#property version   "1.00"
#property strict

input double InpMaxRiskPct    = 1.5;
input double InpMinRR         = 1.5;
input double InpMaxLots       = 5.0;
input double InpMaxAggRiskPct = 4.0;
input int    InpMagic         = 80085;
input bool   InpDryRun        = true;
input int    InpPollMs        = 5000;

string   gSigFile   = "zpt_signals.csv";
string   gStateFile = "zpt_state.json";

double ValuePerLotPerUnit(string sym)
{
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) ts = 1e-9;
   return tv / ts;
}

double NormLots(string sym, double lots)
{
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double minL = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step) * step;
   lots = MathMin(lots, MathMin(maxL, InpMaxLots));
   if(lots < minL) lots = minL;
   return NormalizeDouble(lots, 2);
}

double AggOpenRiskPct()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0) equity = 1;
   double openRisk = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() != InpMagic) continue;
      if(OrderType() != OP_BUY && OrderType() != OP_SELL) continue;
      double sl = OrderStopLoss();
      if(sl <= 0) continue;
      string s  = OrderSymbol();
      double dist = MathAbs(OrderOpenPrice() - sl);
      openRisk += dist * OrderLots() * ValuePerLotPerUnit(s);
   }
   return (openRisk / equity) * 100.0;
}

bool HasOpen(string sym)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() == InpMagic && OrderSymbol() == sym) return true;
   }
   return false;
}

void WriteState()
{
   int h = FileOpen(gStateFile, FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(h == INVALID_HANDLE) return;
   string js = StringFormat(
      "{\"ts\":%d,\"balance\":%.2f,\"equity\":%.2f,\"margin_free\":%.2f,"
      "\"open_positions\":%d,\"agg_open_risk_pct\":%.3f,\"dry_run\":%s}",
      (int)TimeCurrent(),
      AccountInfoDouble(ACCOUNT_BALANCE),
      AccountInfoDouble(ACCOUNT_EQUITY),
      AccountInfoDouble(ACCOUNT_MARGIN_FREE),
      PositionsTotal(),
      AggOpenRiskPct(),
      InpDryRun ? "true" : "false");
   FileWrite(h, js);
   FileClose(h);
}

void HandleSignal(string line)
{
   string p[];
   int n = StringSplit(line, ',', p);
   if(n < 6) return;
   string sym = p[0]; StringToUpper(sym);
   string side = p[1]; StringToUpper(side);
   double entry = StringToDouble(p[2]);
   double stop  = StringToDouble(p[3]);
   double tgt   = StringToDouble(p[4]);
   double lots  = StringToDouble(p[5]);

   if(!SymbolSelect(sym, true)) { Print("ZptGovEA: unknown symbol ", sym); return; }
   if(stop <= 0) { Print("ZptGovEA REJECT ", sym, " no stop-loss"); return; }
   double risk = MathAbs(entry - stop);
   double rew  = MathAbs(tgt - entry);
   if(risk <= 0 || rew / risk < InpMinRR) { Print("ZptGovEA REJECT ", sym, " RR<", InpMinRR); return; }
   if(HasOpen(sym)) { Print("ZptGovEA SKIP ", sym, " already open (no averaging)"); return; }

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskPerLot = risk * ValuePerLotPerUnit(sym);
   double riskBudget = equity * InpMaxRiskPct / 100.0;
   double maxByRisk = (riskPerLot > 0) ? (riskBudget / riskPerLot) : 0;
   lots = NormLots(sym, MathMin(lots, maxByRisk));

   if(AggOpenRiskPct() + InpMaxRiskPct > InpMaxAggRiskPct)
   { Print("ZptGovEA REJECT ", sym, " agg risk cap"); return; }

   int type = -1;
   if(side == "BUY"  || side == "LONG")  type = OP_BUY;
   if(side == "SELL" || side == "SHORT") type = OP_SELL;
   if(type < 0) { Print("ZptGovEA REJECT ", sym, " bad side ", side); return; }

   if(InpDryRun) { Print("ZptGovEA DRYRUN ", sym, " ", side, " lots=", lots); return; }

   MqlTradeRequest req; MqlTradeResult res;
   ZeroMemory(req); ZeroMemory(res);
   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = sym;
   req.volume    = lots;
   req.type      = (ENUM_ORDER_TYPE)type;
   req.price     = (type == OP_BUY) ? SymbolInfoDouble(sym, SYMBOL_ASK)
                                    : SymbolInfoDouble(sym, SYMBOL_BID);
   req.sl        = stop;
   req.tp        = tgt;
   req.deviation = 10;
   req.magic     = InpMagic;
   req.comment   = "zpt-governed";
   if(!OrderSend(req, res)) Print("ZptGovEA OrderSend FAIL ", res.retcode, " ", res.comment);
   else Print("ZptGovEA OK ticket=", res.order, " ", sym, " ", side, " lots=", lots);
}

int OnInit()
{
   Print("ZptGovEA started. dry_run=", InpDryRun, " maxRisk%=", InpMaxRiskPct);
   EventSetMillisecondTimer(InpPollMs);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { EventKillTimer(); }
void OnTimer()
{
   WriteState();
   int h = FileOpen(gSigFile, FILE_READ|FILE_TXT|FILE_COMMON);
   if(h == INVALID_HANDLE) return;
   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);
      StringTrimLeft(line); StringTrimRight(line);
      if(StringLen(line) == 0) continue;
      if(StringGetCharacter(line, 0) == '#') continue;
      HandleSignal(line);
   }
   FileClose(h);
   // clear the queue so the same signals are never executed twice
   int w = FileOpen(gSigFile, FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(w != INVALID_HANDLE) FileClose(w);
}
void OnTick() {}
//+------------------------------------------------------------------+
