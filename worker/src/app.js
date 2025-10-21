import fs from 'node:fs/promises';
import figlet from 'figlet';
import path from "path";


const main = async () => {
  const { IEXEC_OUT } = process.env;

  let computedJsonObj = {};

  try {
    let messages = [];

    try {

        //const deserializer = new IExecDataProtectorDeserializer();
        // The protected data mock created for the purpose of this Hello World journey
        // contains an object with a key "secretText" which is a string
        //const protectedName = await deserializer.getValue('secretText', 'string');
        //console.log('Found a protected data');
        //messages.push(protectedName);

        const dataPath = path.join(iexecIn, dataFilename);
        const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

        // Access the sensitive data
        const action = data.side; //buy or sell

        console.log(`Processing data for user: ${action}`);

        //1. Start Execution reading ProtectedData
        setTimeout(() => console.log("Starting Execution, reading new order........."), 2000);

        //2. Matching Order
        setTimeout(() => console.log("Order Valid! Matching with order book........."), 1000);
        setTimeout(() => console.log("Matched! Finalize it on chain................."), 3000);

        /*3. Finalize on Chain -TODO:CHECK
          const enclaveSigner = new ethers.Wallet(process.env.ENCLAVE_PRIVATE_KEY);
          const tradeHash = ethers.utils.solidityKeccak256(
              ["address","address","address","address","uint256","uint256","uint256","uint256"],
              Object.values(trade)
          );
          const signature = await enclaveSigner.signMessage(ethers.utils.arrayify(tradeHash));

  // --- Step 4: Connect to blockchain and finalize
          const provider = new ethers.providers.JsonRpcProvider(process.env.ARBITRUM_RPC);
          const settlementContract = new ethers.Contract(CONTRACT_ADDRESS, DarkPoolABI.abi, enclaveSigner);

          const tx = await settlementContract.settle(trade, signature);
          console.log("Trade finalized on-chain:", tx.hash); */


    } catch (e) {
        console.log('It seems there is an issue with protected data:', e);
    }

    const { IEXEC_REQUESTER_SECRET_1, IEXEC_REQUESTER_SECRET_42 } = process.env;
    if (IEXEC_REQUESTER_SECRET_1) {
      const redactedRequesterSecret = IEXEC_REQUESTER_SECRET_1.replace(
        /./g,
        '*'
      );
      console.log(`Got requester secret 1 (${redactedRequesterSecret})!`);
    } else {
      console.log(`Requester secret 1 is not set`);
    }
    if (IEXEC_REQUESTER_SECRET_42) {
      const redactedRequesterSecret = IEXEC_REQUESTER_SECRET_42.replace(
        /./g,
        '*'
      );
      console.log(`Got requester secret 42 (${redactedRequesterSecret})!`);
    } else {
      console.log(`Requester secret 42 is not set`);
    }

    // Transform input text into an ASCII Art text
    const asciiArtText = figlet.textSync(
      `Hello, ${messages.join(' ') || 'World'}!`
    );

    // Write result to IEXEC_OUT
    await fs.writeFile(`${IEXEC_OUT}/result.txt`, asciiArtText);

    // Build the "computed.json" object
    computedJsonObj = {
      'deterministic-output-path': `${IEXEC_OUT}/result.txt`,
    };
  } catch (e) {
    // Handle errors
    console.log(e);

    // Build the "computed.json" object with an error message
    computedJsonObj = {
      'deterministic-output-path': IEXEC_OUT,
      'error-message': 'Oops something went wrong',
    };
  } finally {
    // Save the "computed.json" file
    await fs.writeFile(
      `${IEXEC_OUT}/computed.json`,
      JSON.stringify(computedJsonObj)
    );
  }
};

main();
