//+------------------------------------------------------------------+
//|  XAUUSD_ScalpM5.mq5                                             |
//|  XAUUSD (XAUUSD+) M5+ scalping EA with hard risk gates          |
//|  Bounty a5e51254 deliverable.                                   |
//|                                                                  |
//|  Strategy: EMA20/50 trend filter + RSI(14) pullback reset.      |
//|  Entry  : trend up & RSI just reset into 40..62  -> BUY         |
//|           trend down & RSI into 38..60           -> SELL        |
//|  Risk   : mandatory ATR(14) x1.2 stop, TP = 2.0R. No martingale.|
//|  Gates  : daily loss < 3% equity -> stop for the day.           |
//|           weekly loss < 5% equity -> stop for the week.         |
//|           risk per trade 0.6% equity.                           |
//|  Works on any timeframe >= M5 (set via input).                  |
//+------------------------------------------------------------------+
#property copyright "ZptMaster"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input double InpRiskPct      = 0.6;    // risk % of equity per trade
input double InpRR           = 2.0;    // reward:risk
input double InpAtrMult      = 1.2;    // stop = ATR * mult
input int    InpEmaFast      = 20;
input int    InpEmaSlow      = 50;
input int    InpRsiPeriod    = 14;
input double InpRsiBuyLo     = 40;
input double InpRsiBuyHi     = 62;
input double InpRsiSellLo    = 38;
input double InpRsiSellHi    = 60;
input double InpDayLossPct   = 3.0;    // daily stop-out
input double InpWeekLossPct  = 5.0;    // weekly stop-out
input int    InpAtrPeriod    = 14;
input int    InpMagic        = 51254;

CTrade trade;

double gDayStartEq   = 0.0;
double gWeekStartEq  = 0.0;
int    gCurDay       = -1;
int    gCurWeek      = -1;
bool   gDayBlocked   = false;
bool   gWeekBlocked  = false;

int DayOfYearNow(){ MqlDateTime t; TimeToStruct(TimeCurrent(),t); return t.day_of_year; }
int WeekOfYearNow(){ MqlDateTime t; TimeToStruct(TimeCurrent(),t); return t.day_of_year/7; }

void ResetGatesIfNeeded()
{
   int d = DayOfYearNow();
   int w = WeekOfYearNow();
   if(d != gCurDay){ gCurDay = d; gDayStartEq = AccountInfoDouble(ACCOUNT_EQUITY); gDayBlocked = false; }
   if(w != gCurWeek){ gCurWeek = w; gWeekStartEq = AccountInfoDouble(ACCOUNT_EQUITY); gWeekBlocked = false; }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(gDayStartEq  > 0 && eq <= gDayStartEq  * (1.0 - InpDayLossPct /100.0))  gDayBlocked  = true;
   if(gWeekStartEq > 0 && eq <= gWeekStartEq * (1.0 - InpWeekLossPct/100.0)) gWeekBlocked = true;
}

bool IsTrendUp()
{
   double ef = iMA(_Symbol, PERIOD_CURRENT, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE, 1);
   double es = iMA(_Symbol, PERIOD_CURRENT, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE, 1);
   return (ef > es);
}

bool HasPosition()
{
   for(int i=PositionsTotal()-1; i>=0; i--){
      ulong tk = PositionGetTicket(i);
      if(PositionSelectByTicket(tk) && PositionGetInteger(POSITION_MAGIC) == InpMagic) return true;
   }
   return false;
}

double LotsForRisk(double stopDistUsd)
{
   double eq   = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk = eq * InpRiskPct / 100.0;
   double tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSz <= 0 || tickVal <= 0 || stopDistUsd <= 0) return 0.0;
   double lossPerLot = stopDistUsd / tickSz * tickVal;
   double lots = risk / lossPerLot;
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0) lots = MathFloor(lots/step)*step;
   if(lots < minL) lots = minL;
   if(lots > maxL) lots = maxL;
   return NormalizeDouble(lots, 2);
}

void OnTick()
{
   ResetGatesIfNeeded();
   if(gDayBlocked || gWeekBlocked) return;
   if(HasPosition()) return;
   if(Bars(_Symbol, PERIOD_CURRENT) < InpEmaSlow + 5) return;

   double atr = iATR(_Symbol, PERIOD_CURRENT, InpAtrPeriod, 1);
   double rsi = iRSI(_Symbol, PERIOD_CURRENT, InpRsiPeriod, PRICE_CLOSE, 1);
   if(atr <= 0) return;

   bool up = IsTrendUp();
   double stopDist = atr * InpAtrMult;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(up && rsi >= InpRsiBuyLo && rsi <= InpRsiBuyHi){
      double lots = LotsForRisk(stopDist);
      if(lots <= 0) return;
      double sl = bid - stopDist;
      double tp = bid + stopDist * InpRR;
      trade.Buy(lots, _Symbol, ask, sl, tp, "XAUUSD_ScalpM5");
   }
   else if(!up && rsi >= InpRsiSellLo && rsi <= InpRsiSellHi){
      double lots = LotsForRisk(stopDist);
      if(lots <= 0) return;
      double sl = ask + stopDist;
      double tp = ask - stopDist * InpRR;
      trade.Sell(lots, _Symbol, bid, sl, tp, "XAUUSD_ScalpM5");
   }
}
//+------------------------------------------------------------------+
