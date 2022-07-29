class BidDistributionParams:
    def __init__(self, treasury: float, partner: float, stake: float, burn: float):
        self.treasury = treasury
        self.partner = partner
        self.stake = stake
        self.burn = burn
        self.user = 1 - treasury - partner - stake - burn


class ProtocolParams:
    def __init__(self, target_bid_percent: float, bid_distribution: BidDistributionParams):
        self.target_bid_percent = target_bid_percent
        self.bid_distribution = bid_distribution


class EcosystemParams:
    def __init__(self, mev_volume_ratio: float, user_claim_percent: float, partner_claim_percent: float):
        self.mev_volume_ratio = mev_volume_ratio
        self.user_claim_percent = user_claim_percent
        self.partner_claim_percent = partner_claim_percent


class DAOParams:
    def __init__(self, daily_treasury_burn: float):
        self.daily_treasury_burn = daily_treasury_burn


class VolumeParams:
    def __init__(self, start_volume: float, volume_growth_rate: float, max_volume: float):
        self.start_volume = start_volume
        self.volume_growth_rate = volume_growth_rate
        self.max_volume = max_volume
