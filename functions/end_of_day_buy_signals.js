const {onSchedule} = require("firebase-functions/v2/scheduler");
const logger = require("firebase-functions/logger");
const admin = require("firebase-admin");

if (!admin.apps.length) {
  admin.initializeApp();
}

const db = admin.firestore();

/**
 * 장 마감 후 stock_analysis의 buy_signal만 pending_orders로 반영한다.
 * - 기본 스케줄: 평일 15:40 (KST)
 * - 대상 마켓: BOT_MARKET 환경변수 (기본 KR)
 */
exports.refreshPendingOrdersFromBuySignals = onSchedule(
  {
    schedule: "40 15 * * 1-5",
    timeZone: "Asia/Seoul",
  },
  async () => {
    const market = process.env.BOT_MARKET || "KR";
    const date = new Date().toISOString().slice(0, 10);

    logger.info("[EOD] start refresh", {market, date});

    const signalsSnap = await db
      .collection("stock_analysis")
      .where("type", "==", "buy_signal")
      .where("market", "==", market)
      .get();

    if (signalsSnap.empty) {
      logger.info("[EOD] no buy signals", {market, date});
      return;
    }

    let batch = db.batch();
    let opCount = 0;
    let upserted = 0;

    for (const doc of signalsSnap.docs) {
      const data = doc.data() || {};
      const stockId = data.id || doc.id;
      const code = stockId.includes("_") ? stockId.split("_", 2)[1] : stockId;

      if (!code) {
        continue;
      }

      const orderId = `${market}_${code}`;
      const ref = db.collection("pending_orders").doc(orderId);

      batch.set(
        ref,
        {
          code,
          name: data.name || code,
          market,
          status: "ready",
          signalType: "buy_signal",
          sourceAnalysisId: doc.id,
          date,
          updatedAt: admin.firestore.FieldValue.serverTimestamp(),
        },
        {merge: true},
      );

      opCount += 1;
      upserted += 1;

      if (opCount >= 450) {
        await batch.commit();
        batch = db.batch();
        opCount = 0;
      }
    }

    if (opCount > 0) {
      await batch.commit();
    }

    logger.info("[EOD] refresh complete", {
      market,
      date,
      sourceSignals: signalsSnap.size,
      upserted,
    });
  },
);
