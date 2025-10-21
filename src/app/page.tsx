"use client";

import {useEffect, useState} from "react";
import {useAppKit} from "@reown/appkit/react";
import {useAccount, useDisconnect, useChainId, useSwitchChain} from "wagmi";
import {
    IExecDataProtector,
    IExecDataProtectorCore,

    ProtectedData,
    GrantedAccess,
} from "@iexec/dataprotector";

import WelcomeBlock from "@/components/WelcomeBlock";
import wagmiNetworks, {explorerSlugs} from "@/config/wagmiNetworks";

// External Link Icon Component
const ExternalLinkIcon = () => (
    <svg
        className="inline-block w-3 h-3 ml-1"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
    >
        <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
        />
    </svg>
);

export default function Home() {
    const {open} = useAppKit();
    const {disconnectAsync} = useDisconnect();
    const {isConnected, connector} = useAccount();
    const chainId = useChainId();
    const {switchChain} = useSwitchChain();

    const [dataProtectorCore, setDataProtectorCore] =
        useState<IExecDataProtectorCore | null>(null);
    const [dataToProtect, setDataToProtect] = useState({data: "",});
    const [protectedData, setProtectedData] = useState<ProtectedData>();
    const [isLoadingSell, setIsLoadingSell] = useState(false);
    const [isLoadingBuy, setIsLoadingBuy] = useState(false);

    const [grantedAccess, setGrantedAccess] = useState<GrantedAccess>();
    const [isGrantingAccess, setIsGrantingAccess] = useState(false);

    const networks = Object.values(wagmiNetworks);

    const login = () => {
        open({view: "Connect"});
    };

    const logout = async () => {
        try {
            await disconnectAsync();
        } catch (err) {
            console.error("Failed to logout:", err);
        }
    };

    const handleChainChange = async (
        event: React.ChangeEvent<HTMLSelectElement>
    ) => {
        const selectedChainId = parseInt(event.target.value);
        if (selectedChainId && selectedChainId !== chainId && switchChain) {
            try {
                await switchChain({chainId: selectedChainId});
            } catch (error) {
                console.error("Failed to switch chain:", error);
            }
        }
    };

    // Get explorer URL for current chain using iExec explorer
    const getExplorerUrl = (
        address: string | undefined,
        type: "address" | "dataset" | "apps" = "address"
    ) => {
        const explorerSlug = explorerSlugs[chainId];
        if (!explorerSlug) return null;

        if (!address) return `https://explorer.iex.ec/${explorerSlug}/${type}`;
        return `https://explorer.iex.ec/${explorerSlug}/${type}/${address}`;
    };

    useEffect(() => {
        const initializeDataProtector = async () => {
            if (isConnected && connector) {
                try {
                    const provider =
                        (await connector.getProvider()) as import("ethers").Eip1193Provider;
                    const dataProtector = new IExecDataProtector(provider, {
                        allowExperimentalNetworks: true,
                    });
                    setDataProtectorCore(dataProtector.core);
                } catch (error) {
                    console.error("Failed to initialize data protector:", error);
                }
            }
        };

        initializeDataProtector().then(r => console.log(r));
    }, [isConnected, connector]);

    const grantDataAccess = async (data?: ProtectedData) => {
        if (!dataProtectorCore || !data) return;

        if (dataProtectorCore) {
            setIsGrantingAccess(true);
            try {
                const result = await dataProtectorCore.grantAccess({
                    protectedData: data.address,
                    authorizedApp: "0x9B0A0Fc519e7DE7E310e51C8b8583AF827fDa720", //todo put to env
                    authorizedUser: data.owner,
                    pricePerAccess: 2000000000,
                    numberOfAccess: 500,
                    onStatusUpdate: ({title, isDone}) => {
                        console.log(title, isDone);
                    },
                });

                console.log("result from grantAccess:", result);
                setGrantedAccess(result);


                const result2 = await dataProtectorCore.getGrantedAccess({
                    protectedData: data.address,
                    authorizedApp: "0x9B0A0Fc519e7DE7E310e51C8b8583AF827fDa720", //todo put to env
                    authorizedUser: data.owner,
                });
                console.log("result from getGrantedAccess: ", result2);

            } catch (error) {
                console.error("Error granting access:", error);
            } finally {
                setIsGrantingAccess(false);
            }


            try {
                const process = await dataProtectorCore.processProtectedData({
                    protectedData: data.address,
                    app: '0x9B0A0Fc519e7DE7E310e51C8b8583AF827fDa720',
                    appMaxPrice: 3000000000, // 5 nRLC budget (enough for 2 + 2 nRLC)
                    //workerpool: "0xB967057a21dc6A66A29721d96b8Aa7454B7c383F", // 👈 use the pool you found
                });
                console.log("process from processProtectedData: ", process);

            } catch (error) {
                console.error("Error process Protected Data:", error);
            } finally {
                setIsGrantingAccess(false);
            }
        }
    };

    /*const processProtectedData = async (data?: ProtectedData) => {
        if (!dataProtectorCore || !data) return;
        if (isGrantingAccess) {
            setIsDataProcessing(true);
            try {
                const response = await dataProtectorCore.processProtectedData({
                    protectedData: data.address,
                    app: '0x9B0A0Fc519e7DE7E310e51C8b8583AF827fDa720',
                });
                console.info("Responde from Process Protected Data:", response);
                setIsDataProcessing(true);
            } catch (error) {
                console.error("Error processing data:", error);
            } finally {
                setIsGrantingAccess(false);
            }
        }
    };*/

    const protectData = async (event: { preventDefault: () => void }) => {
        event.preventDefault();
        if (dataProtectorCore) {
            setIsLoadingBuy(true);
            setIsLoadingSell(true)
            try {
                const protectedData = await dataProtectorCore.protectData({
                    name: Math.random().toFixed().toString().slice(2, 11),
                    data: {
                        data: dataToProtect.data,
                    },
                });

                console.log("Protected Data:", protectedData);
                setProtectedData(protectedData);

                await grantDataAccess(protectedData);
            } catch (error) {
                console.error("Error protecting data:", error);
            } finally {
                setIsLoadingBuy(true);
                setIsLoadingSell(true);
            }
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-5 text-center">
            <nav className="bg-[#F4F7FC] rounded-xl p-4 mb-8 flex justify-between items-center">
                <div className="flex items-center gap-6">
                    <div className="font-mono text-xl font-bold text-gray-800">
                        iDarkPool
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    {isConnected && (
                        <div className="flex items-center gap-2">
                            <label
                                htmlFor="chain-selector"
                                className="text-sm font-medium text-gray-700"
                            >
                                Chain:
                            </label>
                            <select
                                id="chain-selector"
                                value={chainId}
                                onChange={handleChainChange}
                                className="chain-selector"
                            >
                                {networks?.map((network) => (
                                    <option key={network.id} value={network.id}>
                                        {network.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                    {!isConnected ? (
                        <button onClick={login} className="primary">
                            Connect my wallet
                        </button>
                    ) : (
                        <button onClick={logout} className="secondary">
                            Disconnect
                        </button>
                    )}
                </div>
            </nav>

            <WelcomeBlock/>

            <section className="p-8 bg-[#F4F7FC] rounded-xl text-center content-center">
                {isConnected ? (
                    <div>
                        <h2 className="mb-6 text-2xl font-semibold text-gray-800">
                            Make your Trade on IDP/PYUSD (1 IDR = 1 $ PYUSD)
                        </h2>
                        <form onSubmit={protectData} className="mb-8 space-x-6">

                            <button
                                disabled={isLoadingBuy || isLoadingSell}
                                onClick={() => {
                                    //MOCKED
                                    setDataToProtect(() => ({
                                        data: 'buy'
                                    }))
                                }}
                                className="primary "
                                type="submit"
                            >
                                Buy 1 IDP
                            </button>

                            <button
                                disabled={isLoadingBuy || isLoadingSell}
                                onClick={() => {
                                    //MOCKED
                                    setDataToProtect(() => ({
                                        data: 'sell'
                                    }))
                                }}
                                type="submit"
                                className="secondary"
                            >
                                Sell 1 IDP
                            </button>

                        </form>

                        {protectedData && (
                            <div className="bg-blue-100 border border-blue-300 rounded-xl p-6 mt-6">
                                <h3 className="text-blue-800 mb-4 text-lg font-semibold">
                                    ✅ Trade protected successfully!
                                </h3>
                                <div className="text-blue-800 space-y-2 text-sm">
                                    <p>
                                        <strong>Name:</strong> {protectedData.name}
                                    </p>
                                    <p>
                                        <strong>Address:</strong> {protectedData.address}
                                        {getExplorerUrl(protectedData.address, "dataset") && (
                                            <a
                                                href={getExplorerUrl(protectedData.address, "dataset")!}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="ml-2 inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors"
                                            >
                                                View Trade Protected Data <ExternalLinkIcon/>
                                            </a>
                                        )}
                                    </p>
                                    <p>
                                        <strong>Owner:</strong> {protectedData.owner}
                                        {getExplorerUrl(protectedData.owner, "address") && (
                                            <a
                                                href={getExplorerUrl(protectedData.owner, "address")!}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="ml-2 inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors"
                                            >
                                                View Address
                                                <ExternalLinkIcon/>
                                            </a>
                                        )}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Grant Access Form */}
                        <div className="mt-12 pt-8 border-t border-gray-200">

                            {grantedAccess && (
                                <div className="bg-blue-100 border border-blue-300 rounded-xl p-6 mt-6">
                                    <h3 className="text-blue-800 mb-4 text-lg font-semibold">
                                        ✅ Trade Access granted to Worker successfully!
                                    </h3>
                                    <div className="text-blue-800 space-y-2 text-sm">
                                        <p>
                                            <strong>Protected Data:</strong> {grantedAccess.dataset}
                                            {getExplorerUrl(grantedAccess.dataset, "dataset") && (
                                                <a
                                                    href={
                                                        getExplorerUrl(grantedAccess.dataset, "dataset")!
                                                    }
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="ml-2 inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors"
                                                >
                                                    View Protected Data
                                                    <ExternalLinkIcon/>
                                                </a>
                                            )}
                                        </p>
                                        <p>
                                            <strong>Protected Data Price:</strong>{" "}
                                            {grantedAccess.datasetprice} nRLC
                                        </p>
                                        <p>
                                            <strong>Volume:</strong> {grantedAccess.volume}
                                        </p>
                                        <p>
                                            <strong>iApp Restrict:</strong> {grantedAccess.apprestrict}
                                        </p>
                                        <p>
                                            <strong>Workerpool Restrict:</strong>{" "}
                                            {grantedAccess.workerpoolrestrict}
                                        </p>
                                        <p>
                                            <strong>Requester Restrict:</strong>{" "}
                                            {grantedAccess.requesterrestrict}
                                            {grantedAccess.requesterrestrict !==
                                                "0x0000000000000000000000000000000000000000" &&
                                                getExplorerUrl(
                                                    grantedAccess.requesterrestrict,
                                                    "address"
                                                ) && (
                                                    <a
                                                        href={
                                                            getExplorerUrl(
                                                                grantedAccess.requesterrestrict,
                                                                "address"
                                                            )!
                                                        }
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="ml-2 inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors"
                                                    >
                                                        View Requester
                                                        <ExternalLinkIcon/>
                                                    </a>
                                                )}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                        {/* Get Task Status */}
                        {/* TODO */}
                    </div>
                ) : (
                    <div className="text-center py-12 px-6">
                        <h2 className="mb-4 text-xl text-gray-600">
                            Connect your wallet to get started
                        </h2>
                        <p className="text-gray-500 mb-6">
                            You need to connect your wallet to use data protection features.
                        </p>
                        <button onClick={login} className="primary">
                            Connect my wallet
                        </button>
                    </div>
                )}
            </section>
        </div>
    );
}
