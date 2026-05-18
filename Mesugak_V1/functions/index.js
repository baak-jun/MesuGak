/**
 * Import function triggers from their respective submodules:
 *
 * const {onCall} = require("firebase-functions/v2/https");
 * const {onDocumentWritten} = require("firebase-functions/v2/firestore");
 *
 * See a full list of supported triggers at https://firebase.google.com/docs/functions
 */

const {setGlobalOptions} = require("firebase-functions");

setGlobalOptions({maxInstances: 10});

const {refreshPendingOrdersFromBuySignals} = require("./end_of_day_buy_signals");

exports.refreshPendingOrdersFromBuySignals = refreshPendingOrdersFromBuySignals;
