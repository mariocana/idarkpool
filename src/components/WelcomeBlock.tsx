import React from "react";

const WelcomeBlock: React.FC = () => {
  return (
    <div className="bg-gradient-to-br dark:from-[#82828E] dark:to-[#82828E00] from-[#E0E4F6] to-[#F4F7FC] rounded-2xl p-12 md:p-8 mb-8 text-gray-800 text-center">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl md:text-3xl font-bold mb-4 text-gray-800">
          Welcome to the iDarkPool
        </h1>
        <p className="text-xl md:text-lg mb-8 text-gray-700 leading-relaxed">
          Connect your wallet to protect your SWAP on the blockchain.
        </p>

        <div className="mb-8">
          <a
            href="https://mariocana.cloud/"
            target="_blank"
            rel="noopener noreferrer"
            className="secondary"
          >
            🌐 Develop by mariocana.eth
          </a>
        </div>
      </div>
    </div>
  );
};

export default WelcomeBlock;
