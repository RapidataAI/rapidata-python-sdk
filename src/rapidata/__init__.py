"""Rapidata Python SDK: human feedback at scale through ``RapidataClient``.

Coding agents: do not infer usage from this source tree. Read the maintained
guide first with ``python -m rapidata skill`` (``--install`` keeps it in the
project) or at https://docs.rapidata.ai/llms-full.txt. Check authentication with
``python -m rapidata status`` and log the user in with ``python -m rapidata login``.
"""

__version__ = "3.25.7"

from ._agent_hint import print_agent_hint as _print_agent_hint

_print_agent_hint()

from .rapidata_client import (
    RapidataClient,
    RapidataAudience,
    RapidataAudienceBase,
    RapidataAudienceManager,
    RapidataFilteredAudience,
    RecruitingMetrics,
    RapidataJob,
    RapidataJobDefinition,
    RapidataJobManager,
    CostEstimate,
    JobProgress,
    RapidataSignal,
    RapidataSignalManager,
    RapidataFlow,
    RapidataRankingFlow,
    RapidataClassifyFlow,
    FlowItemResult,
    ClassifyFlowItemResult,
    ClassifyDatapointResult,
    BillingPeriod,
    RapidataBillingManager,
    ValidationSetManager,
    RapidataValidationSet,
    Box,
    RapidataResults,
    BenchmarkDemographicDimension,
    DemographicSelection,
    LabelingSelection,
    EffortSelection,
    RapidataRetrievalMode,
    ValidationSelection,
    ConditionalValidationSelection,
    CappedSelection,
    ShufflingSelection,
    # --- GENERATED SETTINGS IMPORTS START ---
    RapidataSettings,
    CustomSetting,
    NoShuffleSetting,
    MuteVideoSetting,
    FreeTextMinimumCharactersSetting,
    FreeTextMaxCharactersSetting,
    SwapContextInstructionSetting,
    PlayPercentageVideoSetting,
    MarkdownSetting,
    AllowNeitherBothSetting,
    OriginalLanguageOnlySetting,
    NoMistakeOptionSetting,
    DisableAutoloopSetting,
    NoInstructionDisplaySetting,
    KeyboardNumericSetting,
    LocateMaxPointsSetting,
    LocateMinPointsSetting,
    ComparePanoramaSetting,
    CompareEquirectangularSetting,
    ClassifyEquirectangularSetting,
    # --- GENERATED SETTINGS IMPORTS END ---
    CountryFilter,
    LanguageFilter,
    NotFilter,
    OrFilter,
    AndFilter,
    UserScoreFilter,
    CampaignFilter,
    AgeFilter,
    GenderFilter,
    CustomFilter,
    AgeGroup,
    Gender,
    DeviceFilter,
    DeviceType,
    Tag,
    Origin,
    VoteAggregation,
    Datapoint,
    ContextManager,
    FailedUploadException,
    FailedUpload,
    SampleUpload,
    rapidata_config,
    logger,
    managed_print,
    CompressionConfig,
)

from . import types
